"""
RiskBudgetController — TIA v3 portfolio risk guard.

Professional funds always maintain a systematic risk budget that scales down
exposure as portfolio drawdown increases. This module implements both:

  1. A deterministic hard-cap version used in btc_env.py (clear, interpretable,
     not differentiable — just a tiered lookup).

  2. A differentiable soft version for use as a feature in the actor's policy net
     (smooth approximation of the same tiers via linear decay + clamp).

The actor sees risk_budget as a 1-dim input and learns to scale its requested
position size accordingly. The env ALSO applies the hard cap independently,
creating a belt-and-suspenders safety mechanism:

  Final pos = min(actor_base × gate_mult, POS_SIZE_MAX × hard_budget)

Drawdown tiers (from config):
  DD < 10%  → budget = 1.00  (full exposure)
  DD ≥ 10%  → budget = 0.70  (-30%)
  DD ≥ 20%  → budget = 0.50  (-50%)
  DD ≥ 30%  → budget = 0.25  (-75%)
"""

from __future__ import annotations

import torch

from DRL_BTC.config import (
    RISK_BUDGET_DD_10, RISK_BUDGET_DD_20, RISK_BUDGET_DD_30, RISK_BUDGET_MIN,
)


class RiskBudgetController:
    """
    Deterministic (non-neural) portfolio risk scaling.

    Used in two ways:
      • btc_env.py: hard cap applied directly to pos_size_act each step
      • actor_critic.py: soft tensor version to produce a policy net input feature

    Example
    ───────
    >>> rbc = RiskBudgetController()
    >>> rbc.compute(current_dd=0.15)   # → 0.70
    >>> rbc.compute(current_dd=0.25)   # → 0.50
    """

    # Tier table: (dd_lower_bound, budget_multiplier) — descending threshold order
    _TIERS = [
        (0.30, RISK_BUDGET_DD_30),
        (0.20, RISK_BUDGET_DD_20),
        (0.10, RISK_BUDGET_DD_10),
        (0.00, 1.00),
    ]

    @classmethod
    def compute(cls, current_dd: float) -> float:
        """
        Non-differentiable tiered lookup.

        Parameters
        ──────────
        current_dd : float ∈ [0, 1]  — current drawdown from equity peak

        Returns
        ───────
        budget : float ∈ [RISK_BUDGET_MIN, 1.0]
        """
        for threshold, budget in cls._TIERS:
            if current_dd >= threshold:
                return float(budget)
        return 1.0

    @staticmethod
    def compute_tensor(neg_dd: torch.Tensor) -> torch.Tensor:
        """
        Differentiable soft version for use as policy net input feature.

        Approximates the tiered lookup with a smooth linear-decay + clamp:
            budget = max(0.25, 1.0 - 3.0 × DD)

        This gives approximately:
            DD = 0.0  → 1.00
            DD = 0.1  → 0.70  (target 0.70)
            DD = 0.2  → 0.40  (target 0.50, slight conservatism OK)
            DD = 0.3  → 0.10  (clamp to RISK_BUDGET_MIN=0.25)

        Parameters
        ──────────
        neg_dd : (B,) ∈ [-1, 0]  — neg_dd portfolio feature from btc_env
                                    (neg_dd = −DD, so DD = −neg_dd)

        Returns
        ───────
        budget : (B,) ∈ [RISK_BUDGET_MIN, 1.0]
        """
        dd     = (-neg_dd).clamp(0.0, 1.0)                            # (B,) ∈ [0, 1]
        budget = (1.0 - 3.0 * dd).clamp(RISK_BUDGET_MIN, 1.0)
        return budget
