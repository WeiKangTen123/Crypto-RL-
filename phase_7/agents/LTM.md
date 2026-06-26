# Phase 7 Tuner Agent — Long-Term Memory

## Agent: @phase7-tuner
Purpose: Track parameter range adjustments, probe outcomes, and lessons learned across sessions.

Entry format: `[YYYY-MM-DD HH:MM] | {PATTERN} | {DETAIL}`

---

## Historical Insights & Constraints

- Range widening by 60% of span has been effective in practice — avoids over-widening while giving the optimizer room to explore.
- Params hitting the upper bound are more common than lower bound hits (optimizer tends to push period-type params higher).
- Boolean params (`trend_filter`, `use_trend_filter`, `require_confirmation`) are categorical — no boundary concept, always left as `[True, False]`.
- MICRO windows (1M, 2M) have fewer bars so early stopping fires more often — probe results from these windows may be noisier than MESO/MACRO.

## Adjustment Log

- **2026-06-16 11:52**: Strategy 99 (IchimokuKeltnerSqueezeStrategy): probe completed — all ranges adequate.
- **2026-06-16 11:52**: Strategy 1 (MACDKDJStrategy): widened 2 range(s) — kdj_period: (5, 30)→(0, 30) [DEFAULT_RANGES]; max_hold_bars: (4, 48)→(0, 48) [DEFAULT_RANGES]
- **2026-06-16 11:57**: Strategy 93 (NowoIchimokuMTFStrategy): widened 2 range(s) — kijun_period: (10, 60)→(10, 90) [OPTIMIZATION_RANGES]; atr_period: (5, 50)→(5, 77) [OPTIMIZATION_RANGES]
- **2026-06-16 11:58**: Strategy 91 (VWAPATRReversionStrategy): widened 1 range(s) — max_hold_bars: (12, 300)→(12, 473) [OPTIMIZATION_RANGES]
- **2026-06-16 12:01**: Strategy 1 (MACDKDJStrategy): probe completed — all ranges adequate.
- **2026-06-16 12:01**: Strategy 1 (MACDKDJStrategy): probe completed — all ranges adequate.
- **2026-06-16 14:58**: Strategy 36 (VWAPATRReversionStrategy): widened 3 range(s) — atr_period: (10, 100)→(0, 100) [OPTIMIZATION_RANGES]; max_hold_bars: (12, 473)→(12, 750) [OPTIMIZATION_RANGES]; sl_multiplier: (0.5, 3.0)→(0.5, 4.5) [OPTIMIZATION_RANGES]
- **2026-06-16 15:19**: Strategy 36 (VWAPATRReversionStrategy): widened 1 range(s) — multiplier: (1.0, 4.0)→(0, 4) [OPTIMIZATION_RANGES]
- **2026-06-16 15:26**: Strategy 36 (VWAPATRReversionStrategy): widened 2 range(s) — sl_multiplier: (0.5, 4.5)→(0.5, 6.9) [OPTIMIZATION_RANGES]; multiplier: (0, 4)→(0, 4) [OPTIMIZATION_RANGES]