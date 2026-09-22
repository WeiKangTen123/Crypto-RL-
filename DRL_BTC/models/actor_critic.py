"""
LSTM-based Actor-Critic networks for SAC on BTC.

Architecture (Session 10 — TIA v3, v3.1 wiring update)
────────────────────────────────────────────────────────
Input: (batch, seq_len, 217)  — 209 market features + 8 portfolio state

PerspectiveEncoder  (three phases)

  Phase 1 — Semantic Projection
    Each of 9 indicator groups is compressed through a small Linear.

  Phase 2 — Cross-Group Perspective Attention
    9 group embeddings → tokens → MHA (4 heads, d=32).
    Attention weights = interpretable confidence scores at eval time.

  Phase 3 — Temporal Modelling
    LSTM (hidden=LSTM_HIDDEN, 2 layers, dropout=0.1) → z(FC_HIDDEN)

  Group           raw  → proj → attn
  ────────────────────────────────────
  trend      (54) →  32      → 32
  momentum   (57) →  32      → 32
  volatility (21) →  16      → 32
  volume     (21) →  16      → 32
  structure  (30) →  16      → 32
  funding     (6) →   8      → 32
  orderbook   (8) →   8      → 32
  portfolio   (8) →   8      → 32
  signal      (4) →   8      → 32   ← composite: macro/swing/entry/regime
  ────────────────────────────────────
  MHA(d=32, 4 heads) → 288 → LSTM(288, LSTM_HIDDEN, 2L) → FC→ReLU→LN → z(FC_HIDDEN)

Session 10 v3.1 Actor (full decision system):
  z(FC_HIDDEN)
    ├─ BetaEngine        → extract_beta_context (39-dim)
    │    embed(32) + probs(3) + conf(1) + vol(1) + trend(1) + stab(1)
    │    Temperature scaling from DriftManager (calibration drift correction)
    │    + OOD Bayesian dampening toward uniform as ood_score → 1
    ├─ AlphaEngine       → extract_alpha_feat (10-dim)
    │    ret+p50+tp+sl+mfe+mae+conf+var+tail+maxdd
    ├─ MarketDiagnostics → ood_score (1-dim)
    ├─ KnowledgeMemory   → memory_feat (10-dim)  ← v3.1: LIVE DECISION PATH
    │    avg_return+win_rate+mfe+mae+hold+tp_rate+count+sim+conf+regime_match
    │    OOD-gated: ood>0.9 → zeros; ood>0.8 → k=5; ood>0.6 → k=10; else k=20
    ├─ RuleEngine        → rule_feat (3-dim)
    │    rule_direction + rule_confidence + rule_active
    ├─ RiskBudgetController → risk_budget (1-dim)
    │    Soft: max(0.25, 1-3×DD)  [hard cap also applied in btc_env]
    └─ DecisionFusionLayer → gate output (5-dim)
         Inputs: z+beta+alpha+ood+rule+memory+risk (320-dim total)  ← v3.1: +memory+risk
         Outputs: gate_probs(3) + size_mult(1) + gate_conf(1)

  Final fused: [z|beta(39)|alpha(10)|ood(1)|gate(5)|rule(3)|memory(10)|risk(1)]
             = FC_HIDDEN + 69  (vs 59 in TIA v3 / 20 in TIA v2)
  Policy net: FC(FC_HIDDEN+69)→ReLU→FC(FC_HIDDEN//2)→ReLU → mean(4) + log_std(4)

  Position sizing decomposition:
    Actor base_pos × gate_size_mult × env_hard_risk_budget = Final Position

  At inference:  memory_feat from KnowledgeMemory.retrieve_feat(z, ood, regime)
  During training updates: memory_feat from KnowledgeMemory.retrieve_feat_batch() or zeros

Critic  : two independent PerspectiveEncoders + concat(z,a) → Q (twin)
          Structured for future TQC upgrade (return distributions instead of scalar Q).

Feature layout (see feature_builder.py):
  [  0: 18]  trend_1h      [ 61: 79]  trend_4h      [122:140]  trend_1d
  [ 18: 37]  momentum_1h   [ 79: 98]  momentum_4h   [140:159]  momentum_1d
  [ 37: 44]  volatility_1h [ 98:105]  volatility_4h [159:166]  volatility_1d
  [ 44: 51]  volume_1h     [105:112]  volume_4h     [166:173]  volume_1d
  [ 51: 61]  structure_1h  [112:122]  structure_4h  [173:183]  structure_1d
  [183:189]  funding (no TF suffix)
  [189:197]  orderbook (no TF suffix)
  [197:205]  portfolio state (appended by btc_env)
  Portfolio state layout (indices relative to n_market):
    [0] position  [1] pos_size  [2] sl_dist  [3] hold_bars/48
    [4] equity_log  [5] neg_dd  [6] unrealised_pnl  [7] is_holding
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal

from DRL_BTC.config import (
    LSTM_HIDDEN, LSTM_LAYERS, LSTM_DROPOUT,
    FC_HIDDEN, ACTION_DIM, ENTRY_THRESHOLD, MEMORY_FEAT_DIM,
)
from DRL_BTC.models.heads import (
    BetaEngine, AlphaEngine, DecisionFusionLayer,
    extract_beta_context, extract_alpha_feat,
    BETA_FEAT_DIM, ALPHA_FEAT_DIM, RULE_FEAT_DIM,
    # backward-compat aliases
    ConfidenceGate, extract_beta_feat,
)
from DRL_BTC.models.diagnostics import MarketDiagnostics
from DRL_BTC.models.risk_budget import RiskBudgetController
from DRL_BTC.models.opportunity_scorer import OpportunityScorerHead, OPP_SCORE_FEAT_DIM

LOG_STD_MAX =  0.0   # σ_max = 1.0; allows wider action distribution for proper pos-size exploration
LOG_STD_MIN = -3.0   # σ_min = 0.05; keeps some exploration floor

# ── Perspective-attention constants ──────────────────────────────────────────────
D_ATTN  = 32   # common dim each group is projected to before attention
N_HEADS =  4   # self-attention heads (each learns a different "perspective")

# ── Feature group membership ─────────────────────────────────────────────────────
# Maps each indicator's base name (no TF suffix) to its semantic group.
# Unknown names fall back to "structure" with a warning.
_INDICATOR_GROUPS: dict[str, str] = {
    # Trend
    "ema9_ret": "trend",      "ema9_slope": "trend",
    "ema21_ret": "trend",     "ema21_slope": "trend",
    "ema50_ret": "trend",     "ema50_slope": "trend",
    "ema200_ret": "trend",    "ema200_slope": "trend",
    "ema9_21_cross": "trend", "ema21_50_cross": "trend",
    "st_dir": "trend",        "st_dist": "trend",
    "adx": "trend",           "di_diff": "trend",
    "psar_dir": "trend",      "vortex_diff": "trend",
    "hma_slope": "trend",     "ichimoku_dir": "trend",
    # Momentum
    "rsi14": "momentum",      "rsi7": "momentum",       "rsi14_slope": "momentum",
    "macd_hist": "momentum",  "macd_above": "momentum",
    "kdj_j": "momentum",
    "wt1": "momentum",        "wt2": "momentum",        "wt_cross": "momentum",
    "mfi": "momentum",        "cci": "momentum",        "williams_r": "momentum",
    "stoch_k": "momentum",    "stoch_d": "momentum",    "stoch_kd_cross": "momentum",
    "srsi_k": "momentum",
    "fisher": "momentum",     "tsi": "momentum",        "aroon_diff": "momentum",
    # Volatility
    "atr_pct": "volatility",
    "bb_width": "volatility", "bb_pct": "volatility",
    "squeeze": "volatility",  "hist_vol": "volatility",
    "choppiness": "volatility","atr_regime": "volatility",
    # Volume / Flow
    "vol_z": "volume",        "taker_ratio": "volume",  "taker_ratio_z": "volume",
    "vwap_z": "volume",       "cvd_z": "volume",
    "obv_slope": "volume",    "vol_regime": "volume",
    # Structure
    "price_z20": "structure", "vs_ema200": "structure",
    "fvg_bull": "structure",  "fvg_bear": "structure",
    "imb_bull": "structure",  "imb_bear": "structure",
    "swing_hi": "structure",  "swing_lo": "structure",
    "candle": "structure",    "order_block": "structure",
    # Auxiliary — no TF suffix in feature names
    "funding_raw": "funding",      "funding_z20": "funding",
    "funding_mom8h": "funding",    "funding_ma24": "funding",
    "funding_cumsum8h": "funding", "funding_vol20": "funding",
    "ob_imb_1pct": "orderbook",   "ob_imb_3pct": "orderbook",
    "ob_imb_5pct": "orderbook",   "ob_ba_ratio": "orderbook",
    "ob_bid_z": "orderbook",      "ob_ask_z": "orderbook",
    "ob_bid_slope": "orderbook",  "ob_ask_slope": "orderbook",
    # Pre-synthesised composite signals (added by feature_builder._compute_composite_signals)
    "macro_score": "signal",   "swing_score": "signal",
    "entry_score": "signal",   "regime_score": "signal",
    # Open interest (from futures_metrics.parquet — OI changes reveal real conviction)
    "oi_chg":       "openinterest",   # oi_chg_1h + oi_chg_4h both strip to this base
    "oi_z20":       "openinterest",
    "oi_vol_ratio": "openinterest",
    "oi_confirm":   "openinterest",
    "oi_extreme":   "openinterest",
    "oi_mom":       "openinterest",
    # Spot-futures basis (added to funding since both relate to cost of carry)
    "basis_raw":   "funding",
    "basis_z20":   "funding",
    "basis_trend": "funding",
    # Trader positioning / sentiment (L/S ratios from futures_metrics.parquet)
    "ls_ratio_z20":   "sentiment",
    "ls_extreme":     "sentiment",
    "top_ls_z20":     "sentiment",
    "top_retail_div": "sentiment",
    "taker_ls_z20":   "sentiment",

    # On-chain / cycle (Fear & Greed, MVRV proxy, 1yr momentum, ATH drawdown)
    "fng_raw":    "onchain",
    "fng_z60":    "onchain",
    "fng_mom7":   "onchain",
    "mvrv_proxy": "onchain",
    "mvrv_z":     "onchain",
    "yr1_mom":    "onchain",
    "ath_draw":   "onchain",

    # IC-selected alpha library (17 signals: OI crowding, taker, liquidations, funding,
    # net-taker, MA300, coinbase premium, korea premium, market cap, ETH cross,
    # exchange reserve, whale outflows, on-chain contract activity, ETH2, gas, tx median)
    "alpha_lib_oi_z24":    "alpha_lib",
    "alpha_lib_taker_z168": "alpha_lib",
    "alpha_lib_liq_z168":   "alpha_lib",
    "alpha_lib_fund_diff":  "alpha_lib",
    "alpha_lib_net_taker":  "alpha_lib",
    "alpha_lib_alpha300":   "alpha_lib",
    "alpha_lib_cbx_z168":   "alpha_lib",
    "alpha_lib_krx_z12":    "alpha_lib",
    "alpha_lib_mcap_z12":   "alpha_lib",
    "alpha_lib_eth_z12":    "alpha_lib",
    "alpha_lib_xreserve":   "alpha_lib",
    "alpha_lib_xout10":     "alpha_lib",
    "alpha_lib_tx_ext_usd": "alpha_lib",
    "alpha_lib_tx_med":     "alpha_lib",
    "alpha_lib_eth2dep":    "alpha_lib",
    "alpha_lib_gas168":     "alpha_lib",
    "alpha_lib_ccalls":     "alpha_lib",

    # Combo ensemble signals (from Signal_Replay grade-B/C submissions)
    "combo_vote":       "combo",
    "combo_conviction": "combo",
    "combo_long_frac":  "combo",
    "combo_short_frac": "combo",
    "combo_flat_frac":  "combo",
}

# Intermediate projection dim per group (reflects how much information each group carries)
_GROUP_OUT: dict[str, int] = {
    "trend":         32,
    "momentum":      32,
    "volatility":    16,
    "volume":        16,
    "structure":     16,
    "funding":        8,
    "orderbook":      8,
    "portfolio":      8,
    "signal":         8,   # 4 composite signals → 8-dim projection
    "openinterest":  12,   # 7 OI + basis cols → 12-dim
    "sentiment":     12,   # 5 L/S ratio cols → 12-dim
    "alpha_lib":     16,   # 17 IC-selected alpha signals → 16-dim
    "onchain":       10,   # 7 on-chain cols (MVRV, F&G, AdrActive, NVT) → 10-dim
    "combo":          8,   # 5 Signal-Replay ensemble vote/conviction cols → 8-dim
    "strat_signals": 24,   # ~36 BTC strategy position-state cols → 24-dim
}


# ── Perspective Attention ────────────────────────────────────────────────────────

class PerspectiveAttention(nn.Module):
    """
    Cross-group multi-head self-attention.

    At each time step the n_groups projected group vectors are treated as
    "tokens" and fed through multi-head self-attention (N_HEADS=4 heads).
    Each head learns to combine different group subsets — these are the
    agent's emergent "perspectives" (macro, swing, microstructure, risk).

    Attention weights at inference time are interpretable confidence scores:
    a head that attends heavily to trend+funding → macro perspective;
    one that attends to momentum+orderbook → entry-timing perspective, etc.
    """

    def __init__(
        self,
        group_names: list[str],
        group_out:   dict[str, int],
        d_attn:      int = D_ATTN,
        n_heads:     int = N_HEADS,
    ):
        super().__init__()
        self.group_names = group_names
        self.d_attn      = d_attn
        self.n_groups    = len(group_names)

        # Project each group's embedding to the common attention dim (no bias — just rotation)
        self.in_projs = nn.ModuleDict({
            g: nn.Linear(group_out[g], d_attn, bias=False) for g in group_names
        })

        self.mha  = nn.MultiheadAttention(
            embed_dim   = d_attn,
            num_heads   = n_heads,
            dropout     = 0.0,
            batch_first = True,
        )
        self.norm = nn.LayerNorm(d_attn)

    def forward(
        self,
        group_vecs:     dict[str, torch.Tensor],
        return_weights: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        """
        group_vecs : dict g → (batch, seq_len, D_GROUP)
        returns:
            attended     : (batch, seq_len, n_groups * d_attn)
            attn_weights : (batch, seq_len, n_heads, n_groups, n_groups) or None
        """
        batch, seq_len = next(iter(group_vecs.values())).shape[:2]
        n_g = self.n_groups

        # Project each group → d_attn, stack into tokens
        tokens = [self.in_projs[g](group_vecs[g]) for g in self.group_names]
        # (batch, seq_len, n_groups, d_attn) → (batch*seq_len, n_groups, d_attn)
        x = torch.stack(tokens, dim=2).view(batch * seq_len, n_g, self.d_attn)

        if return_weights:
            # average_attn_weights=False → per-head weights (requires PyTorch >= 1.12)
            out, w = self.mha(x, x, x, need_weights=True, average_attn_weights=False)
            # w: (batch*seq_len, n_heads, n_groups, n_groups)
            weights = w.view(batch, seq_len, N_HEADS, n_g, n_g)
        else:
            # need_weights=False skips weight computation — faster during training
            out, _ = self.mha(x, x, x, need_weights=False)
            weights = None

        out      = self.norm(out + x)                              # residual + LN
        attended = out.view(batch, seq_len, n_g * self.d_attn)    # (batch, seq_len, 256)

        return attended, weights


# ── Perspective Encoder ──────────────────────────────────────────────────────────

class PerspectiveEncoder(nn.Module):
    """
    Semantic projection → cross-group attention → LSTM → z.

    The attention layer lets indicator groups "communicate" at each time step,
    enabling the agent to reason about multi-group combinations (perspectives)
    before the LSTM models their temporal evolution.
    """

    def __init__(self, market_cols: list[str], n_portfolio: int):
        super().__init__()

        from collections import defaultdict
        import warnings
        group_idx: dict[str, list[int]] = defaultdict(list)

        for i, col in enumerate(market_cols):
            # Strategy signal columns: strat_{id}_pos → strat_signals group
            if col.startswith("strat_") and col.endswith("_pos"):
                group_idx["strat_signals"].append(i)
                continue
            base = col
            for tf in ("_1h", "_4h", "_1d"):
                if col.endswith(tf):
                    base = col[: -len(tf)]
                    break
            grp = _INDICATOR_GROUPS.get(base)
            if grp is None:
                warnings.warn(
                    f"PerspectiveEncoder: unknown feature '{col}' — assigned to 'structure'"
                )
                grp = "structure"
            group_idx[grp].append(i)

        n_market = len(market_cols)
        group_idx["portfolio"] = list(range(n_market, n_market + n_portfolio))

        # Canonical group order; skip any group with no matching features
        self.group_names: list[str] = [g for g in _GROUP_OUT if group_idx.get(g)]
        self._idx: dict[str, list[int]] = {g: group_idx[g] for g in self.group_names}

        # Phase 1 — semantic projections
        self.projs = nn.ModuleDict({
            g: nn.Linear(len(self._idx[g]), _GROUP_OUT[g])
            for g in self.group_names
        })

        # Phase 2 — cross-group perspective attention
        self.attn = PerspectiveAttention(
            group_names = self.group_names,
            group_out   = {g: _GROUP_OUT[g] for g in self.group_names},
        )

        # Phase 3 — temporal modelling
        lstm_in = len(self.group_names) * D_ATTN   # n_groups × 32
        self.lstm = nn.LSTM(
            input_size  = lstm_in,
            hidden_size = LSTM_HIDDEN,
            num_layers  = LSTM_LAYERS,
            dropout     = LSTM_DROPOUT if LSTM_LAYERS > 1 else 0.0,
            batch_first = True,
        )
        self.fc = nn.Sequential(
            nn.Linear(LSTM_HIDDEN, FC_HIDDEN),
            nn.ReLU(),
            nn.LayerNorm(FC_HIDDEN),
        )
        self._init_lstm()

    def _init_lstm(self):
        for name, p in self.lstm.named_parameters():
            if "weight_ih" in name:   nn.init.xavier_uniform_(p)
            elif "weight_hh" in name: nn.init.orthogonal_(p)
            elif "bias" in name:      nn.init.zeros_(p)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x : (batch, seq_len, n_features) → z : (batch, FC_HIDDEN)"""
        gv = {g: F.relu(self.projs[g](x[..., self._idx[g]])) for g in self.group_names}
        attended, _ = self.attn(gv, return_weights=False)
        out, _ = self.lstm(attended)
        return self.fc(out[:, -1, :])

    def forward_with_attn(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Same as forward() but also returns attention weights.
        Returns:
            z            : (batch, FC_HIDDEN)
            attn_weights : (batch, seq_len, n_heads, n_groups, n_groups)
        """
        gv = {g: F.relu(self.projs[g](x[..., self._idx[g]])) for g in self.group_names}
        attended, weights = self.attn(gv, return_weights=True)
        out, _ = self.lstm(attended)
        return self.fc(out[:, -1, :]), weights


# ── Actor ───────────────────────────────────────────────────────────────────────

# TIA v3.1 + 5-pillar enriched input dimensions for the policy net:
#   z(FC_HIDDEN) + beta(39) + alpha(10) + ood(1) + gate(5) + rule(3) + memory(10) + risk(1) + opp(1)
_OOD_FEAT_DIM  = 1    # MarketDiagnostics ood_score
_GATE_FEAT_DIM = 5    # gate_probs(3) + size_mult(1) + gate_conf(1)
_RISK_FEAT_DIM = 1    # risk_budget scalar from RiskBudgetController
_FUSED_IN_DIM  = (
    FC_HIDDEN + BETA_FEAT_DIM + ALPHA_FEAT_DIM
    + _OOD_FEAT_DIM + _GATE_FEAT_DIM + RULE_FEAT_DIM + MEMORY_FEAT_DIM + _RISK_FEAT_DIM
    + OPP_SCORE_FEAT_DIM
)
# = FC_HIDDEN + 39 + 10 + 1 + 5 + 3 + 10 + 1 + 1 = FC_HIDDEN + 70

# Portfolio feature indices (within the per-bar portfolio state appended by btc_env)
# [0] position  [1] pos_size  [2] sl_dist  [3] hold_bars/48
# [4] equity_log  [5] neg_dd  [6] unrealised_pnl  [7] is_holding
_PORT_NEG_DD_IDX = 5   # neg_dd = -(drawdown) ∈ [-1, 0]


class Actor(nn.Module):
    """
    Session 10 TIA v3.1 — Gaussian policy with the full Decision System.

    Enriched policy net input (FC_HIDDEN + 69):
        z(FC_HIDDEN)     — encoder latent
        beta_ctx(39)     — embed(32)+probs(3)+conf(1)+vol(1)+trend(1)+stab(1)
                            Temperature-scaled (DriftManager) + OOD-dampened
        alpha_feat(10)   — ret+p50+tp+sl+mfe+mae+conf+var+tail+maxdd
        ood_score(1)     — raw OOD score from MarketDiagnostics
        gate_feat(5)     — gate_probs(3)+size_mult(1)+gate_conf(1)
        rule_feat(3)     — rule_dir+rule_conf+rule_active (explicit Rule Engine)
        memory_feat(10)  — KnowledgeMemory compact summary (live decision path)
        risk_budget(1)   — soft DD-based budget from RiskBudgetController

    DriftManager is stored as a Python reference (not nn.Module) and read at
    forward() time to get adaptive temperature + OOD-gated memory retrieval.
    Set by sac_agent after construction: actor_mod._drift_manager = drift_manager.

    KnowledgeMemory is similarly stored as a Python reference.
    Set by sac_agent: actor_mod._knowledge_memory = knowledge_memory.
    At batch=1 inference: real memory_feat is retrieved from KM.
    At batch>1 training:  memory_feat is passed in explicitly (from retrieve_feat_batch)
                          or zeros if not provided.
    """

    def __init__(self, market_cols: list[str], n_portfolio: int):
        super().__init__()
        self.encoder     = PerspectiveEncoder(market_cols, n_portfolio)
        self.beta        = BetaEngine(FC_HIDDEN)
        self.alpha       = AlphaEngine(FC_HIDDEN)
        self.diagnostics = MarketDiagnostics(FC_HIDDEN)
        self.fusion      = DecisionFusionLayer(FC_HIDDEN)
        self.opp_scorer  = OpportunityScorerHead()

        self.net = nn.Sequential(
            nn.Linear(_FUSED_IN_DIM, FC_HIDDEN),
            nn.ReLU(),
            nn.Linear(FC_HIDDEN, FC_HIDDEN // 2),
            nn.ReLU(),
        )
        self.mean_head    = nn.Linear(FC_HIDDEN // 2, ACTION_DIM)
        self.log_std_head = nn.Linear(FC_HIDDEN // 2, ACTION_DIM)

        # Near-zero policy head init — BC pretrain calibrates all biases.
        nn.init.uniform_(self.mean_head.weight, -3e-3, 3e-3)
        nn.init.uniform_(self.mean_head.bias,   -3e-3, 3e-3)
        nn.init.constant_(self.log_std_head.bias,  -2.0)
        nn.init.uniform_(self.log_std_head.weight, -1e-4, 1e-4)

        # Cache signal column indices for fast rule-feat extraction from obs
        n_market = len(market_cols)
        self._macro_idx   = market_cols.index("macro_score")   if "macro_score"   in market_cols else None
        self._swing_idx   = market_cols.index("swing_score")   if "swing_score"   in market_cols else None
        self._regime_idx  = market_cols.index("regime_score")  if "regime_score"  in market_cols else None
        self._neg_dd_idx  = n_market + _PORT_NEG_DD_IDX        # absolute index in obs feature dim

        # References set externally by SACAgent after construction
        self._drift_manager   = None   # DriftManager — for temperature + active OOD gating
        self._knowledge_memory = None  # KnowledgeMemory — for live inference retrieval

    def _extract_rule_feat(self, obs: torch.Tensor) -> torch.Tensor:
        """
        Extract Rule Engine signal from the current (last) bar of obs.

        Returns (B, 3):
          [0] rule_direction   — tanh(combined × 5): soft ∈ [-1, 1]
          [1] rule_confidence  — |combined| clipped to [0, 1]
          [2] rule_active      — 1 if regime > -0.20 AND |combined| > ENTRY_THRESHOLD, else 0

        These make the rule engine's direction signal EXPLICITLY visible to the
        DecisionFusionLayer, allowing it to learn when to trust/override the rule.
        """
        last   = obs[:, -1, :]                                                  # (B, n_feats)
        B      = last.shape[0]
        zeros  = last.new_zeros(B)

        macro  = last[:, self._macro_idx]  if self._macro_idx  is not None else zeros
        swing  = last[:, self._swing_idx]  if self._swing_idx  is not None else zeros
        regime = last[:, self._regime_idx] if self._regime_idx is not None else zeros

        combined     = 0.65 * macro + 0.35 * swing
        rule_dir     = torch.tanh(combined * 5.0)                               # soft direction
        rule_conf    = combined.abs().clamp(0.0, 1.0)                           # signal strength
        rule_active  = (regime > -0.20).float() * (combined.abs() > ENTRY_THRESHOLD).float()

        return torch.stack([rule_dir, rule_conf, rule_active], dim=-1)          # (B, 3)

    def _extract_risk_budget(self, obs: torch.Tensor) -> torch.Tensor:
        """
        Extract soft risk budget from portfolio neg_dd feature.

        Returns (B,) ∈ [0.25, 1.0] via RiskBudgetController.compute_tensor().
        """
        neg_dd = obs[:, -1, self._neg_dd_idx]                  # (B,) ∈ [-1, 0]
        return RiskBudgetController.compute_tensor(neg_dd)     # (B,)

    @staticmethod
    def _build_fused(
        z:           torch.Tensor,
        beta_feat:   torch.Tensor,
        alpha_feat:  torch.Tensor,
        ood_score:   torch.Tensor,
        gate_out:    dict,
        rule_feat:   torch.Tensor,
        memory_feat: torch.Tensor,
        risk_budget: torch.Tensor,
    ) -> torch.Tensor:
        gate_feat = torch.cat([
            gate_out["gate_probs"],                           # (B, 3)
            gate_out["size_multiplier"].unsqueeze(-1),        # (B, 1)
            gate_out["gate_confidence"].unsqueeze(-1),        # (B, 1)
        ], dim=-1)                                            # (B, 5)

        return torch.cat([
            z,                            # FC_HIDDEN
            beta_feat,                    # 39
            alpha_feat,                   # 10
            ood_score.unsqueeze(-1),      #  1
            gate_feat,                    #  5
            rule_feat,                    #  3
            memory_feat,                  # 10
            risk_budget.unsqueeze(-1),    #  1
        ], dim=-1)                        # (B, FC_HIDDEN + 69)

    def forward(self, obs: torch.Tensor, memory_feat: torch.Tensor | None = None):
        """
        obs         : (batch, seq_len, n_features)
        memory_feat : (batch, MEMORY_FEAT_DIM) or None
                      • None / batch>1 from training: pass zeros (or retrieve_feat_batch result)
                      • batch=1 inference: compute from self._knowledge_memory if set

        Returns (action_tanh, log_prob, mean_tanh) — same 3-tuple as all sessions.
        """
        z = self.encoder(obs)
        # Recalibrate OOD stats to CURRENT inference z (B=1, eval mode).
        # Prevents stale running_mean/std (from training-batch updates) causing spurious BLOCK.
        # Also fires for val-rollout actors (deepcopies of _actor_cpu in eval mode),
        # fixing the val stale-diagnostics bug without extra wiring.
        if not torch.compiler.is_compiling() and z.shape[0] == 1 and not self.training:
            self.diagnostics.update(z)
        beta_out   = self.beta(z)
        alpha_out  = self.alpha(z)
        ood_score  = self.diagnostics(z)                      # (B,)

        B = z.shape[0]

        # DriftManager: adaptive temperature for beta calibration
        temperature = (
            self._drift_manager.get_beta_temperature()
            if self._drift_manager is not None else 1.0
        )

        # OOD-corrected + temperature-scaled beta context
        beta_feat  = extract_beta_context(beta_out, ood_score=ood_score,
                                          temperature=temperature)          # (B, 39)
        alpha_feat = extract_alpha_feat(alpha_out)                          # (B, 10)

        # Rule Engine signal
        rule_feat    = self._extract_rule_feat(obs)           # (B, 3)
        risk_budget  = self._extract_risk_budget(obs)         # (B,)

        # Memory feat: live retrieval at batch=1 inference; zeros or explicit at batch>1
        if memory_feat is None:
            if not torch.compiler.is_compiling() and B == 1 and self._knowledge_memory is not None and len(self._knowledge_memory) > 0:
                z_np    = z[0].detach().cpu().numpy()
                ood_v   = float(ood_score[0].item())
                reg_v   = int(beta_out["regime_logits"][0].argmax().item())
                mem_np  = self._knowledge_memory.retrieve_feat(z_np, ood_v, reg_v)
                memory_feat = mem_np.unsqueeze(0).to(z.device)             # (1, 10)
            else:
                memory_feat = z.new_zeros(B, MEMORY_FEAT_DIM)              # (B, 10)

        # DecisionFusion: now receives memory + risk_budget explicitly
        gate_out = self.fusion(z, beta_feat, alpha_feat, ood_score,
                               rule_feat, memory_feat, risk_budget)

        enriched = self._build_fused(z, beta_feat, alpha_feat, ood_score,
                                     gate_out, rule_feat, memory_feat, risk_budget)
        # (B, FC_HIDDEN + 69)

        # Pillar 1: Opportunity Scoring — rates this trade 0-100 from full context
        opp_out       = self.opp_scorer(enriched)
        opp_score_val = opp_out["score"]                              # (B,) ∈ [0, 100]
        enriched      = torch.cat(
            [enriched, (opp_score_val / 100.0).unsqueeze(-1)], dim=-1
        )                                                             # (B, FC_HIDDEN + 70)

        # Stash inference-time scalars for train.py ranking/Kelly.
        # Guard: skipped during torch.compile tracing (GPU); runs only in CPU eager inference.
        if not torch.compiler.is_compiling() and B == 1 and not self.training:
            self._last_actor_info = {
                "opp_score":    float(opp_score_val[0].item()),
                "ret_pred":     float(alpha_out["ret_pred"][0].item()),
                "exp_variance": float(alpha_out["exp_variance"][0].item()),
                "alpha_conf":   float(alpha_out["alpha_confidence"][0].item()),
                "ood_score":    float(ood_score[0].item()),
                "risk_budget":  float(risk_budget[0].item()),
                "rule_active":  float(rule_feat[0, 2].item()),
            }

        h       = self.net(enriched)
        mean    = self.mean_head(h)
        log_std = self.log_std_head(h).clamp(LOG_STD_MIN, LOG_STD_MAX)
        std     = log_std.exp()

        dist     = Normal(mean, std)
        x_t      = dist.rsample()
        y_t      = torch.tanh(x_t)

        log_prob  = dist.log_prob(x_t)
        log_prob -= torch.log(1.0 - y_t.pow(2) + 1e-6)
        log_prob  = log_prob.sum(dim=-1, keepdim=True)

        return y_t, log_prob, torch.tanh(mean)

    @torch.no_grad()
    def act(self, obs: torch.Tensor, deterministic: bool = False) -> torch.Tensor:
        """Single-step inference. Delegates to forward() — single source of truth."""
        action, _, mean = self.forward(obs)
        return mean if deterministic else action

    @torch.no_grad()
    def get_fusion_state(self, obs: torch.Tensor) -> dict:
        """
        Diagnostic: full Decision System state for current obs. Used at eval time.
        """
        z           = self.encoder(obs)
        beta_out    = self.beta(z)
        alpha_out   = self.alpha(z)
        ood_score   = self.diagnostics(z)
        temperature = (
            self._drift_manager.get_beta_temperature()
            if self._drift_manager is not None else 1.0
        )
        beta_feat   = extract_beta_context(beta_out, ood_score=ood_score, temperature=temperature)
        alpha_feat  = extract_alpha_feat(alpha_out)
        rule_feat   = self._extract_rule_feat(obs)
        risk_budget = self._extract_risk_budget(obs)

        B = z.shape[0]
        if not torch.compiler.is_compiling() and B == 1 and self._knowledge_memory is not None and len(self._knowledge_memory) > 0:
            z_np    = z[0].detach().cpu().numpy()
            ood_v   = float(ood_score[0].item())
            reg_v   = int(beta_out["regime_logits"][0].argmax().item())
            mem_np  = self._knowledge_memory.retrieve_feat(z_np, ood_v, reg_v)
            memory_feat = mem_np.unsqueeze(0).to(z.device)
        else:
            memory_feat = z.new_zeros(B, MEMORY_FEAT_DIM)

        gate_out   = self.fusion(z, beta_feat, alpha_feat, ood_score,
                                rule_feat, memory_feat, risk_budget)
        fused_diag = self._build_fused(z, beta_feat, alpha_feat, ood_score,
                                       gate_out, rule_feat, memory_feat, risk_budget)
        opp_out    = self.opp_scorer(fused_diag)
        return {
            # Beta
            "beta_regime":      beta_out["regime_logits"].argmax(dim=-1),
            "beta_embedding":   beta_out["regime_embedding"],
            "beta_vol":         beta_out["vol_pred"],
            "beta_trend_conf":  beta_out["trend_confidence"],
            "beta_stability":   beta_out["regime_stability"],
            "beta_trans_prob":  beta_out["transition_prob"],
            "beta_temperature": temperature,
            # Alpha
            "alpha_ret":        alpha_out["ret_pred"],
            "alpha_tp_prob":    alpha_out["tp_prob"],
            "alpha_sl_prob":    alpha_out["sl_prob"],
            "alpha_conf":       alpha_out["alpha_confidence"],
            "alpha_exp_var":    alpha_out["exp_variance"],
            "alpha_tail_risk":  alpha_out["tail_risk"],
            "alpha_exp_maxdd":  alpha_out["exp_max_dd"],
            # Rule Engine
            "rule_direction":   rule_feat[:, 0],
            "rule_confidence":  rule_feat[:, 1],
            "rule_active":      rule_feat[:, 2],
            # Memory
            "memory_feat":      memory_feat,
            "memory_n":         len(self._knowledge_memory) if self._knowledge_memory else 0,
            # OOD + Gate + Risk
            "ood_score":        ood_score,
            "gate_decision":    gate_out["gate_probs"].argmax(dim=-1),
            "gate_size_mult":   gate_out["size_multiplier"],
            "gate_conf":        gate_out["gate_confidence"],
            "risk_budget":      risk_budget,
            # Opportunity score (Pillar 1)
            "opp_score":        opp_out["score"],
            "opp_components":   opp_out["components"],
        }

    @torch.no_grad()
    def get_perspective_weights(self, obs: torch.Tensor) -> torch.Tensor:
        """
        Returns per-head attention weights for the last time step (current bar).
        Shape: (n_heads, n_groups, n_groups)
        """
        _, weights = self.encoder.forward_with_attn(obs)
        return weights[0, -1]   # last bar: (n_heads, n_groups, n_groups)


# ── Twin Critics ────────────────────────────────────────────────────────────────

class Critic(nn.Module):
    """
    Twin Q-networks. Each has its own PerspectiveEncoder so the critic can
    learn an independent feature representation from the actor.
    """

    def __init__(self, market_cols: list[str], n_portfolio: int):
        super().__init__()
        self.enc1 = PerspectiveEncoder(market_cols, n_portfolio)
        self.enc2 = PerspectiveEncoder(market_cols, n_portfolio)
        self.q1 = nn.Sequential(
            nn.Linear(FC_HIDDEN + ACTION_DIM, FC_HIDDEN), nn.ReLU(),
            nn.Linear(FC_HIDDEN, FC_HIDDEN // 2),         nn.ReLU(),
            nn.Linear(FC_HIDDEN // 2, 1),
        )
        self.q2 = nn.Sequential(
            nn.Linear(FC_HIDDEN + ACTION_DIM, FC_HIDDEN), nn.ReLU(),
            nn.Linear(FC_HIDDEN, FC_HIDDEN // 2),         nn.ReLU(),
            nn.Linear(FC_HIDDEN // 2, 1),
        )

    def forward(self, obs: torch.Tensor, action: torch.Tensor):
        """Returns (q1, q2)."""
        z1  = self.enc1(obs)
        z2  = self.enc2(obs)
        sa1 = torch.cat([z1, action], dim=-1)
        sa2 = torch.cat([z2, action], dim=-1)
        return self.q1(sa1), self.q2(sa2)


# ── Convenience factory ─────────────────────────────────────────────────────────

def make_networks(
    market_cols:  list[str],
    n_portfolio:  int,
    device:       torch.device,
):
    """Build actor, critic, and frozen target critic from feature column names."""
    actor      = Actor(market_cols, n_portfolio).to(device)
    critic     = Critic(market_cols, n_portfolio).to(device)
    critic_tgt = Critic(market_cols, n_portfolio).to(device)
    critic_tgt.load_state_dict(critic.state_dict())
    for p in critic_tgt.parameters():
        p.requires_grad_(False)
    return actor, critic, critic_tgt
