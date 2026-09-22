"""
Opportunity Scoring Layer — Pillar 1 of the 5-pillar ROI plan.

OpportunityScorerHead runs on the same 325-dim post-fusion context as the policy
net (AFTER DecisionFusionLayer, BEFORE the final FC layers) and produces:
  score       (B,)   ∈ [0, 100]   — composite opportunity quality signal
  components  (B, 7) ∈ [0, 1]    — interpretability breakdown (logging only)

The score feeds:
  • Pillar 2 (TradeRanker) — rolling-percentile skip filter
  • Pillar 3 (KellySizer)  — opportunity_factor in safe Kelly formula
  • Policy net             — score/100 appended to fused vector (+1 dim)
"""

from __future__ import annotations

import torch
import torch.nn as nn

from DRL_BTC.config import (
    FC_HIDDEN, MEMORY_FEAT_DIM,
    OPP_SCORE_THRESH_SKIP, OPP_SCORE_THRESH_5PCT,
    OPP_SCORE_THRESH_10PCT, OPP_SCORE_THRESH_15PCT,
    OPP_SCORE_THRESH_20PCT, POS_SIZE_MAX,
)
from DRL_BTC.models.heads import BETA_FEAT_DIM, ALPHA_FEAT_DIM, RULE_FEAT_DIM

# Input dimensionality = Actor._build_fused() output before opp_score is appended:
#   z(FC_HIDDEN) + beta(39) + alpha(10) + ood(1) + gate(5) + rule(3) + memory(10) + risk(1)
_OPP_OOD_DIM  = 1
_OPP_GATE_DIM = 5   # gate_probs(3) + size_mult(1) + gate_conf(1)
_OPP_RISK_DIM = 1
FUSED_PRE_OPP_DIM = (
    FC_HIDDEN + BETA_FEAT_DIM + ALPHA_FEAT_DIM
    + _OPP_OOD_DIM + _OPP_GATE_DIM + RULE_FEAT_DIM + MEMORY_FEAT_DIM + _OPP_RISK_DIM
)
# = 256 + 39 + 10 + 1 + 5 + 3 + 10 + 1 = 325

OPP_SCORE_FEAT_DIM = 1   # scalar (score/100) appended to fused vector

_N_COMPONENTS = 7   # interpretability decomposition channels


class OpportunityScorerHead(nn.Module):
    """
    Rates every candidate trade 0–100 from the full post-fusion decision context.

    Architecture: 3-layer MLP with LN → sigmoid → scale to [0, 100].
    A parallel 2-layer branch produces 7 interpretability components.
    """

    def __init__(self, in_dim: int = FUSED_PRE_OPP_DIM):
        super().__init__()
        self.score_net = nn.Sequential(
            nn.Linear(in_dim, 256), nn.LayerNorm(256), nn.ReLU(),
            nn.Linear(256, 128),   nn.LayerNorm(128), nn.ReLU(),
            nn.Linear(128, 64),    nn.ReLU(),
            nn.Linear(64, 1),
        )
        self.component_net = nn.Sequential(
            nn.Linear(in_dim, 128), nn.ReLU(),
            nn.Linear(128, _N_COMPONENTS),
            nn.Sigmoid(),
        )
        # Start near 50 so scores don't collapse to poles early in training
        nn.init.constant_(self.score_net[-1].bias, 0.0)
        nn.init.uniform_(self.score_net[-1].weight, -1e-3, 1e-3)

    def forward(self, fused: torch.Tensor) -> dict:
        """
        fused : (B, FUSED_PRE_OPP_DIM)
        Returns dict with:
          score      (B,)   ∈ [0, 100]
          components (B, 7) ∈ [0, 1]
        """
        raw        = self.score_net(fused).squeeze(-1)    # (B,)
        score      = torch.sigmoid(raw) * 100.0           # [0, 100]
        components = self.component_net(fused)            # (B, 7)
        return {"score": score, "components": components}


def score_to_position_size(score: float) -> float:
    """Tiered position size (fraction of equity) from opportunity score."""
    if score < OPP_SCORE_THRESH_SKIP:   return 0.0
    if score < OPP_SCORE_THRESH_5PCT:   return 0.05
    if score < OPP_SCORE_THRESH_10PCT:  return 0.10
    if score < OPP_SCORE_THRESH_15PCT:  return 0.15
    if score < OPP_SCORE_THRESH_20PCT:  return 0.20
    return float(POS_SIZE_MAX)
