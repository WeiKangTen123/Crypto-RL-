"""
LSTM-based Actor-Critic networks for SAC on BTC.

Architecture (Session 9)
────────────────────────
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

Session 9 Actor (target architecture):
  z(FC_HIDDEN)
    ├─ BetaHead  → regime_probs(3) + vol(1) + trend(1)  = 5-dim beta_feat
    ├─ AlphaHead → ret+mfe+mae+tp_prob+hold              = 5-dim alpha_feat
    └─ DecisionFusionHead → dir_probs(3) + confidence(1) = 4-dim fusion_feat
  Concatenate: [z | beta_feat | alpha_feat | fusion_feat] → (FC_HIDDEN + 14)
  Policy net: FC(FC_HIDDEN+14)→ReLU→FC(FC_HIDDEN//2)→ReLU → mean(4) + log_std(4)

  Heads stay ACTIVE during RL (not dropped after pretrain).
  SharedModel.copy_encoder_to() transfers encoder + all 3 head weights to Actor.

Critic  : two independent PerspectiveEncoders + concat(z,a) → Q (twin)

Feature layout (see feature_builder.py):
  [  0: 18]  trend_1h      [ 61: 79]  trend_4h      [122:140]  trend_1d
  [ 18: 37]  momentum_1h   [ 79: 98]  momentum_4h   [140:159]  momentum_1d
  [ 37: 44]  volatility_1h [ 98:105]  volatility_4h [159:166]  volatility_1d
  [ 44: 51]  volume_1h     [105:112]  volume_4h     [166:173]  volume_1d
  [ 51: 61]  structure_1h  [112:122]  structure_4h  [173:183]  structure_1d
  [183:189]  funding (no TF suffix)
  [189:197]  orderbook (no TF suffix)
  [197:205]  portfolio state (appended by btc_env)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal

from DRL_BTC.config import (
    LSTM_HIDDEN, LSTM_LAYERS, LSTM_DROPOUT,
    FC_HIDDEN, ACTION_DIM,
)
from DRL_BTC.models.heads import BetaHead, AlphaHead, DecisionFusionHead

LOG_STD_MAX =  0.0   # σ_max = 1.0; prevents exploding stochasticity
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
        lstm_in = len(self.group_names) * D_ATTN   # 8 × 32 = 256
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

# Dimension of the enriched input to the policy net:
#   z(FC_HIDDEN) + beta_feat(5) + alpha_feat(5) + fusion_feat(4)
_BETA_FEAT_DIM   = 5   # regime_probs(3) + vol(1) + trend(1)
_ALPHA_FEAT_DIM  = 5   # ret + mfe + mae + tp_prob + hold
_FUSION_FEAT_DIM = 4   # dir_probs(3) + confidence(1)
_FUSED_IN_DIM    = FC_HIDDEN + _BETA_FEAT_DIM + _ALPHA_FEAT_DIM + _FUSION_FEAT_DIM


class Actor(nn.Module):
    """
    Session 9 — Gaussian policy with BetaHead + AlphaHead + DecisionFusionHead
    active during RL.

    The policy net receives an enriched input:
        [z | beta_regime_probs | beta_vol | beta_trend |
             alpha_ret | alpha_mfe | alpha_mae | alpha_tp | alpha_hold |
             fusion_dir_probs | fusion_confidence]
    = FC_HIDDEN + 14 dimensions.

    This gives the actor direct read-access to:
      • Regime classification (bull/bear/range) — from BetaHead
      • Predicted trade quality (expected return, MFE, MAE) — from AlphaHead
      • Learned direction decision (LONG/SHORT/WAIT) + confidence — from Fusion
    The actor can output pos_size≈0 to soft-skip trades the fusion head marks WAIT.

    forward() still returns the same (action, log_prob, mean) 3-tuple so
    sac_agent.py requires no changes.
    """

    def __init__(self, market_cols: list[str], n_portfolio: int):
        super().__init__()
        self.encoder = PerspectiveEncoder(market_cols, n_portfolio)

        # Session 9: heads active during RL (weights warm-started from SharedModel pretrain)
        self.beta   = BetaHead(FC_HIDDEN)
        self.alpha  = AlphaHead(FC_HIDDEN)
        self.fusion = DecisionFusionHead(FC_HIDDEN)

        # Policy net input = z + all head feature summaries
        self.net = nn.Sequential(
            nn.Linear(_FUSED_IN_DIM, FC_HIDDEN),
            nn.ReLU(),
            nn.Linear(FC_HIDDEN, FC_HIDDEN // 2),
            nn.ReLU(),
        )
        self.mean_head    = nn.Linear(FC_HIDDEN // 2, ACTION_DIM)
        self.log_std_head = nn.Linear(FC_HIDDEN // 2, ACTION_DIM)

        # Near-zero policy head init — BC pretrain calibrates all biases.
        # With mean≈0: decoded params start at midpoint of each range.
        nn.init.uniform_(self.mean_head.weight, -3e-3, 3e-3)
        nn.init.uniform_(self.mean_head.bias,   -3e-3, 3e-3)
        nn.init.constant_(self.log_std_head.bias,  -2.0)   # σ≈0.14 → tracks BC mean
        nn.init.uniform_(self.log_std_head.weight, -1e-4, 1e-4)

    @staticmethod
    def _build_fused(
        z:          torch.Tensor,
        beta_out:   dict,
        alpha_out:  dict,
        fusion_out: dict,
    ) -> torch.Tensor:
        regime_probs = F.softmax(beta_out["regime_logits"], dim=-1)      # (B, 3)
        beta_feat = torch.cat([
            regime_probs,
            beta_out["vol_pred"].unsqueeze(-1),
            beta_out["trend_pred"].unsqueeze(-1),
        ], dim=-1)                                                         # (B, 5)

        alpha_feat = torch.cat([
            alpha_out["ret_pred"].unsqueeze(-1),
            alpha_out["mfe_pred"].unsqueeze(-1),
            alpha_out["mae_pred"].unsqueeze(-1),
            alpha_out["tp_prob"].unsqueeze(-1),
            alpha_out["hold_pred"].unsqueeze(-1),
        ], dim=-1)                                                         # (B, 5)

        dir_probs = F.softmax(fusion_out["direction_logits"], dim=-1)    # (B, 3)
        fusion_feat = torch.cat([
            dir_probs,
            fusion_out["confidence"].unsqueeze(-1),
        ], dim=-1)                                                         # (B, 4)

        return torch.cat([z, beta_feat, alpha_feat, fusion_feat], dim=-1) # (B, FC_HIDDEN+14)

    def forward(self, obs: torch.Tensor):
        """
        obs : (batch, seq_len, n_features)
        returns (action_tanh, log_prob, mean_tanh)  — same signature as Session 7/8.
        """
        z          = self.encoder(obs)
        beta_out   = self.beta(z)
        alpha_out  = self.alpha(z)
        fusion_out = self.fusion(z, beta_out, alpha_out)
        enriched   = self._build_fused(z, beta_out, alpha_out, fusion_out)

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
        Diagnostic: returns all head predictions for the current observation.
        Useful at eval time to inspect what the agent "thinks" about the regime.

        Returns dict with keys:
            beta_regime   : (B,) — 0=BULL, 1=BEAR, 2=RANGE
            beta_vol      : (B,) — predicted forward vol
            beta_trend    : (B,) — predicted trend strength
            alpha_ret     : (B,) — expected signed trade return
            alpha_tp_prob : (B,) — P(TP hit)
            fusion_dir    : (B,) — 0=LONG, 1=SHORT, 2=WAIT
            fusion_conf   : (B,) — [0,1] confidence in direction decision
        """
        z          = self.encoder(obs)
        beta_out   = self.beta(z)
        alpha_out  = self.alpha(z)
        fusion_out = self.fusion(z, beta_out, alpha_out)
        return {
            "beta_regime":   beta_out["regime_logits"].argmax(dim=-1),
            "beta_vol":      beta_out["vol_pred"],
            "beta_trend":    beta_out["trend_pred"],
            "alpha_ret":     alpha_out["ret_pred"],
            "alpha_tp_prob": alpha_out["tp_prob"],
            "fusion_dir":    fusion_out["direction_logits"].argmax(dim=-1),
            "fusion_conf":   fusion_out["confidence"],
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
