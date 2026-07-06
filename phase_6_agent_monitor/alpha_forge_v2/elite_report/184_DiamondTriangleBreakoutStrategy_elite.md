---
status: PAPER_READY
id: 184
grade: GOOD
date: 2026-07-03
---
# Elite Report: DiamondTriangleBreakoutStrategy (ID 184)

## Final Metrics
| Metric | Value |
|---|---|
| Total Return | +837.37% |
| Annual Return | +51.23% |
| Sharpe Ratio | **1.26** |
| Sortino Ratio | 1.95 |
| Calmar Ratio | 1.81 |
| Max Drawdown | **28.24%** |
| Profit Factor | 1.45 |
| Win Rate | 39.23% |
| Total Trades | 209 (5.5 yr) |
| Avg Notional | $6,112/trade |

## Yearly Performance
| Year | Return |
|---|---|
| 2021 | +73.68% |
| 2022 | **+64.46%** |
| 2023 | +68.47% |
| 2024 | **+129.69%** |
| 2025 | -5.46% |
| 2026 | -10.30% |

**4/6 years strongly positive** including 2022 bear market.

## Optimized Parameters
```
bb_period      = 13
bb_std         = 1.5704    ← tighter bands = earlier squeeze detection
squeeze_pct    = 0.0586
squeeze_bars   = 3         ← floor boundary (⚠ may benefit from expansion)
vol_period     = 27
vol_spike_mult = 1.4286
adx_period     = 11
adx_threshold  = 24.69
atr_period     = 8
sl_atr_mult    = 2.0913
atr_trail_mult = 3.6772
```

## Edge Summary
Shorter BB period (13) detects micro-squeezes faster. Tighter bb_std (1.57) means the squeeze threshold is more discriminating — only genuine low-volatility compression triggers. ATR trail (3.68×) lets winners run well past the breakout. 2022 and 2023 trending markets were ideal for this strategy.

## Warning
`squeeze_bars=3` hit the floor boundary during finetune — the optimizer wanted to go below 3 but was blocked. Consider expanding OPTIMIZATION_RANGES minimum to 1 and re-finetuning.

## Correlation Warning
Should be checked against ID 42 (BBW Volatility Breakout) — both use BB squeeze as the core detector.

## Deployment Recommendation
Ready for paper trading. Standard 10× leverage, 10% risk/trade. Watch 2025–2026 trending regime — low-volatility compression logic underperforms in sideways drift.

---
*Dev Report:* `dev_report/Volatility_Breakout/20260703_184_DiamondTriangleBreakoutStrategy_dev.md`
*Factor Card:* `factor_library/Volatility_Breakout/20260526_diamond_triangle_breakout.md`
