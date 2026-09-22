"""
Dynamic Risk Allocation — Pillar 3 of the 5-pillar ROI plan.

Safe Kelly Criterion with multi-factor discounting:
  f_raw   = μ / σ²                              (raw Kelly)
  f_safe  = min(f_raw, KELLY_CAP) × KELLY_FRACTION   (quarter-Kelly safety)
  f_final = f_safe × ood_discount × conf × memory_factor × opp_factor × risk_budget

All inputs are expected to come from the CPU actor's _last_actor_info dict
and KnowledgeMemory.win_rate(), available after each select_action() call.
"""

from __future__ import annotations

import numpy as np

from DRL_BTC.config import (
    KELLY_FRACTION, KELLY_CAP,
    POS_SIZE_MIN, POS_SIZE_MAX,
)


class KellySizer:
    """Computes safe Kelly position size with multi-factor discounting."""

    # Minimum viable position when trade_ranker has already approved the trade.
    # Prevents bootstrapping deadlock: if ret_pred ≤ 0 early in training → Kelly=0 →
    # no trades → no replay experience → model never learns → perpetually stuck.
    _MIN_SIZE = 0.05

    def compute(
        self,
        ret_pred:          float,
        exp_variance:      float,
        alpha_conf:        float,
        ood_score:         float,
        memory_win_rate:   float,
        opportunity_score: float,
        risk_budget:       float = 1.0,
    ) -> float:
        """
        Returns position fraction in [_MIN_SIZE, POS_SIZE_MAX].

        Parameters
        ----------
        ret_pred          expected return ∈ ℝ  (AlphaEngine ret_pred)
        exp_variance      return variance ≥ 0   (AlphaEngine exp_variance)
        alpha_conf        confidence ∈ [0, 1]   (AlphaEngine alpha_confidence)
        ood_score         novelty ∈ [0, 1]      (MarketDiagnostics; 1 = fully OOD)
        memory_win_rate   win rate ∈ [0, 1]     (KnowledgeMemory.win_rate())
        opportunity_score ∈ [0, 100]            (OpportunityScorerHead)
        risk_budget       ∈ [0.25, 1.0]         (RiskBudgetController)
        """
        mu  = max(0.0, float(ret_pred))
        var = max(float(exp_variance), 1e-4)

        kelly_raw  = min(mu / var, float(KELLY_CAP))
        kelly_safe = kelly_raw * float(KELLY_FRACTION)    # quarter-Kelly

        ood_discount  = 1.0 - float(ood_score) * 0.8     # OOD → shrink; 0 OOD → full
        conf_factor   = 0.5 + 0.5 * float(alpha_conf)    # [0.5, 1.0]
        memory_factor = 0.5 + 0.5 * float(memory_win_rate)  # [0.5, 1.0]
        opp_factor    = float(opportunity_score) / 100.0     # [0.0, 1.0]

        pos = (
            kelly_safe
            * ood_discount
            * conf_factor
            * memory_factor
            * opp_factor
            * float(risk_budget)
        )

        pos = float(np.clip(pos, 0.0, float(POS_SIZE_MAX)))
        # Floor: trade_ranker already approved this trade; ensure minimum viable size
        # so the model gets feedback even when alpha head is pessimistic early in training.
        return max(pos, self._MIN_SIZE)
