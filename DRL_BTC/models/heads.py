"""
TIA v3 prediction heads (Session 10, v3.1 wiring update).

BetaEngine        : Regime intelligence + 32-d regime embedding + vol class + transition prob
AlphaEngine       : Full return distribution + risk heads (exp_variance, tail_risk, exp_max_dd)
DecisionFusionLayer: Fuses z + Beta + Alpha + OOD + Rule + Memory + RiskBudget → EXECUTE/REDUCE/SKIP

New in TIA v3 vs TIA v2:
  BetaEngine:
    • 32-d regime_embedding (richer latent than 3 probs alone)
    • vol_class head (Low/Med/High 3-way classification)
    • transition_prob head (P regime changes in next 24 bars)
    • OOD + temperature correction: extract_beta_context() dampens regime probs toward uniform
      proportional to OOD severity; DriftManager supplies adaptive temperature when overconfident
  AlphaEngine:
    • exp_variance head (variance of log-returns over hold period)
    • tail_risk head  (peak-to-trough max drawdown during hold)
    • exp_max_dd head (max cumulative adverse excursion)

New in v3.1 (wiring update):
  extract_beta_context:
    • temperature parameter: T>1 smooths regime probs (DriftManager calibration correction)
  DecisionFusionLayer:
    • Now receives memory_feat (10-dim) from KnowledgeMemory — live decision path
    • Now receives risk_budget (1-dim) — gate can choose SKIP instead of just shrinking size
    • in_dim: z(256) + beta(39) + alpha(10) + ood(1) + rule(3) + memory(10) + risk(1) = 320

Feature vector dimensions (used to set _FUSED_IN_DIM in actor_critic.py):
    extract_beta_context  → 39-dim   (embed(32) + probs(3) + conf(1) + vol(1) + trend(1) + stab(1))
    extract_alpha_feat    → 10-dim   (old 7 + exp_var(1) + tail_risk(1) + max_dd(1))
    rule_feat             →  3-dim   (rule_direction + rule_confidence + rule_active)
    memory_feat           → 10-dim   (avg_return/win_rate/mfe/mae/hold/tp_rate/count/sim/conf/regime)
    OOD score             →  1-dim
    DecisionFusionLayer   →  5-dim   (gate_probs×3 + size_mult×1 + gate_conf×1)
    risk_budget           →  1-dim   (drawdown-based scalar from RiskBudgetController)
    Total enrichment      : 69  (vs 59 in TIA v3 / 20 in TIA v2)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from DRL_BTC.config import OOD_BLOCK_THRESH, RULE_FEAT_DIM, MEMORY_FEAT_DIM


# ── Architecture constants ────────────────────────────────────────────────────

BETA_EMBED_DIM = 32     # regime embedding dimension
_BETA_H_DIM    = 256    # BetaEngine internal hidden dim (fixed regardless of z_dim)

# extract_beta_context() output layout (39-d total):
#   [0:32]  regime_embedding  — 32-d latent regime representation
#   [32:35] regime_probs      — P(BULL), P(BEAR), P(RANGE) after optional OOD correction
#   [35]    regime_conf       — max(regime_probs): certainty of dominant regime
#   [36]    vol_pred          — forward realized vol ∈ [0, 1]
#   [37]    trend_confidence  — trend clarity ∈ [0, 1]
#   [38]    regime_stability  — P(regime stays same for N bars) ∈ [0, 1]
BETA_FEAT_DIM  = 39

# extract_alpha_feat() output layout (10-d total):
#   [0]  ret_pred          — mean expected signed trade return
#   [1]  ret_p50           — median expected return
#   [2]  tp_prob           — P(TP hit before SL)
#   [3]  sl_prob           — P(SL hit before TP)
#   [4]  mfe_pred          — max favorable excursion (≥0)
#   [5]  mae_pred          — max adverse excursion from entry (≥0)
#   [6]  alpha_confidence  — meta-confidence (RL-calibrated, no supervised label)
#   [7]  exp_variance      — variance of log-returns over hold period (≥0)
#   [8]  tail_risk         — max intraperiod drawdown from rolling peak (≥0)
#   [9]  exp_max_dd        — expected peak-to-trough max drawdown during hold (≥0)
ALPHA_FEAT_DIM = 10


# ── Feature-extraction helpers ────────────────────────────────────────────────

def extract_beta_context(
    beta_out:    dict,
    ood_score:   torch.Tensor | None = None,
    temperature: float               = 1.0,
) -> torch.Tensor:
    """
    39-dim beta context for policy net input.

    Two calibration corrections applied in order:
      1. Temperature scaling (DriftManager calibration drift):
             regime_logits / T   — T>1 smooths overconfident reads
      2. OOD Bayesian dampening (MarketDiagnostics):
             corrected = (1-ood)×probs + ood×uniform(1/3)
             prevents "BULL 95%" read when market is OOD

    Parameters
    ──────────
    beta_out    : dict output from BetaEngine.forward()
    ood_score   : (B,) ∈ [0, 1] from MarketDiagnostics; None = no OOD correction
    temperature : float ≥ 1.0 from DriftManager.get_beta_temperature();
                  1.0 = no change, 3.0 = heavily smoothed (overconfident model)

    Returns
    ───────
    (B, 39) tensor
    """
    logits = beta_out["regime_logits"]
    if temperature != 1.0:
        logits = logits / max(temperature, 1e-6)
    regime_probs = F.softmax(logits, dim=-1)                          # (B, 3)

    if ood_score is not None:
        weight       = ood_score.unsqueeze(-1).clamp(0.0, 1.0)       # (B, 1)
        uniform      = torch.full_like(regime_probs, 1.0 / 3.0)
        regime_probs = (1.0 - weight) * regime_probs + weight * uniform

    regime_conf = regime_probs.max(dim=-1, keepdim=True).values       # (B, 1)

    return torch.cat([
        beta_out["regime_embedding"],                                  # 32
        regime_probs,                                                  #  3
        regime_conf,                                                   #  1
        beta_out["vol_pred"].unsqueeze(-1),                            #  1
        beta_out["trend_confidence"].unsqueeze(-1),                    #  1
        beta_out["regime_stability"].unsqueeze(-1),                    #  1
    ], dim=-1)                                                         # → (B, 39)


def extract_alpha_feat(alpha_out: dict) -> torch.Tensor:
    """
    10-dim alpha feature for policy net input.

    Layout
    ──────
    [0] ret_pred       [1] ret_p50        [2] tp_prob        [3] sl_prob
    [4] mfe_pred       [5] mae_pred       [6] alpha_conf
    [7] exp_variance   [8] tail_risk      [9] exp_max_dd
    """
    return torch.cat([
        alpha_out["ret_pred"].unsqueeze(-1),           # 1
        alpha_out["ret_p50"].unsqueeze(-1),            # 1
        alpha_out["tp_prob"].unsqueeze(-1),            # 1
        alpha_out["sl_prob"].unsqueeze(-1),            # 1
        alpha_out["mfe_pred"].unsqueeze(-1),           # 1
        alpha_out["mae_pred"].unsqueeze(-1),           # 1
        alpha_out["alpha_confidence"].unsqueeze(-1),   # 1
        alpha_out["exp_variance"].unsqueeze(-1),       # 1
        alpha_out["tail_risk"].unsqueeze(-1),          # 1
        alpha_out["exp_max_dd"].unsqueeze(-1),         # 1
    ], dim=-1)                                         # → (B, 10)


# Backward-compatible alias (used in SharedModel and some analysis scripts)
def extract_beta_feat(beta_out: dict, ood_score: torch.Tensor | None = None) -> torch.Tensor:
    """Alias for extract_beta_context() — returns same 39-dim vector."""
    return extract_beta_context(beta_out, ood_score)


# ── BetaEngine ────────────────────────────────────────────────────────────────

class BetaEngine(nn.Module):
    """
    TIA v3: Regime intelligence with 32-d embedding.

    Architecture
    ────────────
    z (FC_HIDDEN)
      → FC(z_dim) → ReLU → Dropout(0.1)
      → FC(256)   → ReLU
      → h (256-d)

    Heads (all from h):
      embed_head       → regime_embedding (32-d)   — rich latent regime context
      regime_head      → regime_logits (3)          — BULL / BEAR / RANGE
      vol_class_head   → vol_class_logits (3)       — LOW / MED / HIGH vol
      vol_head         → vol_pred (1)               — fwd realized vol ∈ [0, 1]
      trend_conf_head  → trend_confidence (1)        — trend clarity ∈ [0, 1]
      stability_head   → regime_stability (1)        — P(regime same in N bars) ∈ [0, 1]
      transition_head  → transition_prob (1)         — P(regime changes in 24 bars) ∈ [0, 1]
      confidence_head  → calib_confidence (1)        — calibration confidence ∈ [0, 1]

    Supervised labels (Stage 1 pretrain):
      CE(regime_logits, regime_label)
      + 0.5 × CE(vol_class_logits, vol_class_label)
      + 0.5 × MSE(vol_pred, fwd_vol)
      + 0.5 × MSE(trend_confidence, trend_str)
      + 0.5 × BCE(regime_stability, stability_label)
      + 0.3 × BCE(transition_prob, transition_label)
    """

    BULL  = 0
    BEAR  = 1
    RANGE = 2

    VOL_LOW  = 0
    VOL_MED  = 1
    VOL_HIGH = 2

    def __init__(self, z_dim: int = 256):
        super().__init__()
        mid_dim = max(z_dim, 256)
        self.net = nn.Sequential(
            nn.Linear(z_dim, mid_dim), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(mid_dim, _BETA_H_DIM), nn.ReLU(),
        )
        # Embedding head — rich 32-d latent regime representation
        self.embed_head      = nn.Linear(_BETA_H_DIM, BETA_EMBED_DIM)

        # Classification heads
        self.regime_head     = nn.Linear(_BETA_H_DIM, 3)   # BULL / BEAR / RANGE
        self.vol_class_head  = nn.Linear(_BETA_H_DIM, 3)   # LOW / MED / HIGH vol

        # Regression heads (all sigmoid → [0, 1])
        self.vol_head        = nn.Linear(_BETA_H_DIM, 1)
        self.trend_conf_head = nn.Linear(_BETA_H_DIM, 1)
        self.stability_head  = nn.Linear(_BETA_H_DIM, 1)
        self.transition_head = nn.Linear(_BETA_H_DIM, 1)
        self.confidence_head = nn.Linear(_BETA_H_DIM, 1)

    def forward(self, z: torch.Tensor) -> dict:
        h = self.net(z)
        return {
            # Rich embedding (for policy net input via extract_beta_context)
            "regime_embedding":  self.embed_head(h),                                       # (B, 32)
            # Classification
            "regime_logits":     self.regime_head(h),                                      # (B, 3)
            "vol_class_logits":  self.vol_class_head(h),                                   # (B, 3)
            # Regression — all sigmoid → [0, 1]
            "vol_pred":          torch.sigmoid(self.vol_head(h)).squeeze(-1),               # (B,)
            "trend_confidence":  torch.sigmoid(self.trend_conf_head(h)).squeeze(-1),       # (B,)
            "regime_stability":  torch.sigmoid(self.stability_head(h)).squeeze(-1),        # (B,)
            "transition_prob":   torch.sigmoid(self.transition_head(h)).squeeze(-1),       # (B,)
            "calib_confidence":  torch.sigmoid(self.confidence_head(h)).squeeze(-1),       # (B,)
        }

    @torch.no_grad()
    def predict_regime(self, z: torch.Tensor) -> torch.Tensor:
        """Returns predicted regime class (0=BULL, 1=BEAR, 2=RANGE), shape (B,)."""
        return self.forward(z)["regime_logits"].argmax(dim=-1)


# ── AlphaEngine ───────────────────────────────────────────────────────────────

class AlphaEngine(nn.Module):
    """
    TIA v3: Full return distribution + risk metrics.

    Outputs (all from 64-d hidden):
      ret_pred          : (B,)  — mean signed trade return (linear, unbounded)
      ret_p10/p50/p90   : (B,)  — quantile returns (pinball loss)
      mfe_pred          : (B,)  — max favorable excursion ≥ 0 (softplus)
      mae_pred          : (B,)  — max adverse excursion ≥ 0 (softplus)
      tp_prob           : (B,)  — P(TP hit before SL) (sigmoid)
      sl_prob           : (B,)  — P(SL hit before TP) (sigmoid)
      exp_vol           : (B,)  — std of log-returns over hold ≥ 0 (softplus)
      hold_pred         : (B,)  — expected hold duration ≥ 0 (softplus)
      alpha_confidence  : (B,)  — meta-confidence (sigmoid; RL-calibrated only)

      [TIA v3 NEW]:
      exp_variance      : (B,)  — variance of log-returns over hold ≥ 0 (softplus)
                                   (= exp_vol^2 in expectation; different scale)
      tail_risk         : (B,)  — max intraperiod drawdown from rolling peak ≥ 0 (softplus)
      exp_max_dd        : (B,)  — peak-to-trough max cumulative drawdown ≥ 0 (softplus)
    """

    def __init__(self, z_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(z_dim, 128), nn.ReLU(),
            nn.Linear(128, 64),   nn.ReLU(),
        )
        # TIA v2 heads (unchanged)
        self.ret_head      = nn.Linear(64, 1)
        self.quantile_head = nn.Linear(64, 3)   # p10, p50, p90 simultaneously
        self.mfe_head      = nn.Linear(64, 1)
        self.mae_head      = nn.Linear(64, 1)
        self.tp_head       = nn.Linear(64, 1)
        self.sl_head       = nn.Linear(64, 1)
        self.vol_head      = nn.Linear(64, 1)
        self.hold_head     = nn.Linear(64, 1)
        self.conf_head     = nn.Linear(64, 1)
        # TIA v3 risk heads
        self.var_head      = nn.Linear(64, 1)   # exp_variance
        self.tail_head     = nn.Linear(64, 1)   # tail_risk (max rolling drawdown)
        self.maxdd_head    = nn.Linear(64, 1)   # exp_max_dd (peak-to-trough)

    def forward(self, z: torch.Tensor) -> dict:
        h      = self.net(z)
        quants = self.quantile_head(h)   # (B, 3)
        return {
            # TIA v2 outputs
            "ret_pred":        self.ret_head(h).squeeze(-1),
            "ret_p10":         quants[:, 0],
            "ret_p50":         quants[:, 1],
            "ret_p90":         quants[:, 2],
            "mfe_pred":        F.softplus(self.mfe_head(h)).squeeze(-1),
            "mae_pred":        F.softplus(self.mae_head(h)).squeeze(-1),
            "tp_prob":         torch.sigmoid(self.tp_head(h)).squeeze(-1),
            "sl_prob":         torch.sigmoid(self.sl_head(h)).squeeze(-1),
            "exp_vol":         F.softplus(self.vol_head(h)).squeeze(-1),
            "hold_pred":       F.softplus(self.hold_head(h)).squeeze(-1),
            "alpha_confidence":torch.sigmoid(self.conf_head(h)).squeeze(-1),
            # TIA v3 risk outputs
            "exp_variance":    F.softplus(self.var_head(h)).squeeze(-1),
            "tail_risk":       F.softplus(self.tail_head(h)).squeeze(-1),
            "exp_max_dd":      F.softplus(self.maxdd_head(h)).squeeze(-1),
        }


# ── DecisionFusionLayer ───────────────────────────────────────────────────────

class DecisionFusionLayer(nn.Module):
    """
    TIA v3: Fuses encoder z + Beta context + Alpha features + OOD score + Rule signal.

    Renamed from ConfidenceGate (TIA v2) because it does more than gate:
    it synthesises the rule engine's explicit signal WITH the learned predictions
    and OOD awareness into a unified decision context.

    Inputs
    ──────
    z          : (B, z_dim)       — encoder output
    beta_feat  : (B, BETA_FEAT_DIM=39) — from extract_beta_context()
    alpha_feat : (B, ALPHA_FEAT_DIM=10)— from extract_alpha_feat()
    ood_score  : (B,)             — MarketDiagnostics OOD score ∈ [0, 1]
    rule_feat  : (B, RULE_FEAT_DIM=3) — [rule_direction, rule_confidence, rule_active]
                 Makes the rule engine's signal explicitly visible to the fusion layer.
                 Pass zeros during supervised pretraining (no env available).

    Outputs
    ───────
    gate_logits     : (B, 3)  — [EXECUTE, REDUCE, SKIP] unnormalized
    gate_probs      : (B, 3)  — softmax of gate_logits
    size_multiplier : (B,)    — soft fractional size ∈ [0, 1]
                                 = 1.0×P(E) + 0.5×P(R) + 0.0×P(S)
                                 Additionally dampened by OOD block factor
    gate_confidence : (B,)    — sigmoid meta-confidence ∈ [0, 1]

    Not supervised during pretraining — calibrated entirely through RL.
    The rule_feat inputs create a direct gradient path from the rule signal
    to the gate decision, allowing the fusion layer to learn when to trust/override.
    Inputs (v3.1):
    ──────
    z           : (B, z_dim)            — encoder output
    beta_feat   : (B, BETA_FEAT_DIM=39) — from extract_beta_context() (calibrated)
    alpha_feat  : (B, ALPHA_FEAT_DIM=10)— from extract_alpha_feat()
    ood_score   : (B,)                  — MarketDiagnostics OOD score ∈ [0, 1]
    rule_feat   : (B, RULE_FEAT_DIM=3)  — [rule_direction, rule_confidence, rule_active]
    memory_feat : (B, MEMORY_FEAT_DIM=10)— KnowledgeMemory compact summary
                  zeros when memory is empty or OOD > 0.90
    risk_budget : (B,)                  — RiskBudgetController soft scalar ∈ [0.25, 1.0]
                  Gate can choose SKIP when risk_budget is low, rather than just shrinking

    in_dim = z_dim(256) + beta(39) + alpha(10) + ood(1) + rule(3) + memory(10) + risk(1) = 320
    """

    EXECUTE = 0
    REDUCE  = 1
    SKIP    = 2

    def __init__(self, z_dim: int = 256):
        super().__init__()
        in_dim = z_dim + BETA_FEAT_DIM + ALPHA_FEAT_DIM + 1 + RULE_FEAT_DIM + MEMORY_FEAT_DIM + 1
        self.net = nn.Sequential(
            nn.Linear(in_dim, 256), nn.ReLU(),
            nn.Linear(256, 128),   nn.ReLU(),
            nn.Linear(128, 64),    nn.ReLU(),
        )
        self.gate_head       = nn.Linear(64, 3)
        self.confidence_head = nn.Linear(64, 1)
        self.ood_block_thresh = OOD_BLOCK_THRESH

    def forward(
        self,
        z:           torch.Tensor,
        beta_feat:   torch.Tensor,
        alpha_feat:  torch.Tensor,
        ood_score:   torch.Tensor,
        rule_feat:   torch.Tensor,
        memory_feat: torch.Tensor,
        risk_budget: torch.Tensor,
    ) -> dict:
        fused = torch.cat([
            z, beta_feat, alpha_feat, ood_score.unsqueeze(-1),
            rule_feat, memory_feat, risk_budget.unsqueeze(-1),
        ], dim=-1)
        h     = self.net(fused)

        gate_logits = self.gate_head(h)                # (B, 3)
        gate_probs  = F.softmax(gate_logits, dim=-1)   # (B, 3)

        # Soft size multiplier: E[size | gate_probs] ∈ [0, 1]
        _mult     = gate_probs.new_tensor([1.0, 0.5, 0.0])
        size_mult = (gate_probs * _mult).sum(dim=-1)   # (B,)

        # OOD block: further dampen size when ood_score > OOD_BLOCK_THRESH
        # Smooth sigmoid: at thresh=0.9, sigmoid(10*(x-0.9)) → sharp transition
        ood_block_weight = torch.sigmoid(10.0 * (ood_score - self.ood_block_thresh))
        size_mult = size_mult * (1.0 - 0.8 * ood_block_weight)   # max 80% reduction at full OOD

        gate_conf = torch.sigmoid(self.confidence_head(h)).squeeze(-1)   # (B,)

        return {
            "gate_logits":     gate_logits,
            "gate_probs":      gate_probs,
            "size_multiplier": size_mult,
            "gate_confidence": gate_conf,
        }

    @torch.no_grad()
    def predict(
        self,
        z:           torch.Tensor,
        beta_feat:   torch.Tensor,
        alpha_feat:  torch.Tensor,
        ood_score:   torch.Tensor,
        rule_feat:   torch.Tensor,
        memory_feat: torch.Tensor | None = None,
        risk_budget: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns (gate_class, size_multiplier), shapes (B,) each."""
        B = z.shape[0]
        if memory_feat is None:
            memory_feat = z.new_zeros(B, MEMORY_FEAT_DIM)
        if risk_budget is None:
            risk_budget = z.new_ones(B)
        out = self.forward(z, beta_feat, alpha_feat, ood_score, rule_feat, memory_feat, risk_budget)
        return out["gate_probs"].argmax(dim=-1), out["size_multiplier"]


# ── Backward-compatible name aliases ─────────────────────────────────────────
# Kept so any existing scripts importing old class names still work.
# NOTE: ConfidenceGate.forward() now requires rule_feat as 5th argument.
BetaHead           = BetaEngine
AlphaHead          = AlphaEngine
ConfidenceGate     = DecisionFusionLayer
DecisionFusionHead = DecisionFusionLayer
