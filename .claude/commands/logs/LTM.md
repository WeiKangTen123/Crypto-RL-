# Phase 7 Tuner Agent — Long-Term Memory

Format: `[YYYY-MM-DD HH:MM] | {PATTERN} | {DETAIL}`

---

## Historical Insights & Constraints

- Range widening by 60% of span has been effective — avoids over-widening while giving the optimizer room to explore.
- Params hitting the upper bound are more common than lower bound hits (optimizer tends to push period-type params higher).
- Boolean params (`trend_filter`, `use_trend_filter`, `require_confirmation`) are categorical — no boundary concept, always left as `[True, False]`.
- MICRO windows (1M, 2M) have fewer bars — probe results are noisier than MESO/MACRO due to early stopping.

## Adjustment Log

