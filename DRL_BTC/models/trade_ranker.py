"""
Trade Ranking Filter — Pillar 2 of the 5-pillar ROI plan.

Maintains a rolling window of opportunity scores and filters trades to the top
~30% (above the TRADE_RANK_PCTILE-th percentile).  Activates only after
TRADE_RANK_WARMUP scores so the policy is not starved of experience early on.

Usage (train.py):
    ranker = TradeRanker()
    ...
    ranker.record(opp_score)            # called for every candidate trade
    if not ranker.should_execute(opp_score):
        action[0] = -1.0               # force pos_size → 0 (soft-skip)
"""

from __future__ import annotations

from collections import deque

import numpy as np

from DRL_BTC.config import TRADE_RANK_WINDOW, TRADE_RANK_PCTILE, TRADE_RANK_WARMUP


class TradeRanker:
    """Rolling-percentile trade quality filter."""

    def __init__(self) -> None:
        self._scores:    deque[float] = deque(maxlen=TRADE_RANK_WINDOW)
        self._n_seen     = 0
        self._n_executed = 0
        self._n_skipped  = 0

    def record(self, score: float) -> None:
        """Register a new opportunity score (call once per candidate trade signal)."""
        self._scores.append(float(score))
        self._n_seen += 1

    @property
    def threshold(self) -> float:
        """Current cut-off score (0.0 while still in warmup period)."""
        if len(self._scores) < TRADE_RANK_WARMUP:
            return 0.0
        return float(np.percentile(list(self._scores), TRADE_RANK_PCTILE))

    def should_execute(self, score: float) -> bool:
        """True if the score clears the rolling percentile bar."""
        ok = float(score) >= self.threshold
        if ok:
            self._n_executed += 1
        else:
            self._n_skipped += 1
        return ok

    def stats(self) -> dict:
        return {
            "seen":      self._n_seen,
            "executed":  self._n_executed,
            "skipped":   self._n_skipped,
            "threshold": round(self.threshold, 2),
            "exec_rate": self._n_executed / max(self._n_seen, 1),
        }
