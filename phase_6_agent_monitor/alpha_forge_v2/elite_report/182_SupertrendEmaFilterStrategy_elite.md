---
status: PAPER_READY
id: 182
grade: GOOD
date: 2026-07-01
---
# Elite Report: SupertrendEmaFilterStrategy (ID 182)

## Final Metrics
| Metric | Value |
|---|---|
| Total Return | +360.85% |
| Annual Return | +32.63% |
| Sharpe Ratio | **1.63** |
| Sortino Ratio | 2.70 |
| Calmar Ratio | 1.97 |
| Max Drawdown | **16.53%** |
| Profit Factor | 2.25 |
| Win Rate | 57.69% |
| Total Trades | 78 (5.5 yr) |
| Avg Notional | $2,813/trade |

## Yearly Performance
| Year | Return |
|---|---|
| 2021 | +85.77% |
| 2022 | **+45.91%** |
| 2023 | -2.25% |
| 2024 | +27.72% |
| 2025 | +26.92% |
| 2026 | +7.29% |

**5/6 years positive** including 2022 bear market (short side working).

## Optimized Parameters
```
st_period      = 16
st_multiplier  = 4.87    ← key: wide bands = fewer false flips
ema_period     = 177
atr_period     = 13
sl_atr_mult    = 1.86
tp_rr          = 1.83
use_ema_filter = True
```

## Edge Summary
Wide Supertrend bands (multiplier=4.87) act as a strong noise filter — only major trend reversals trigger a flip, eliminating whipsaws that plagued default parameters. EMA-177 macro filter prevents trading against the dominant trend. Both long and short sides contribute to returns.

## Correlation Warning
Should be correlated-checked against ID 20, 61 (SupertrendProStrategy BTC/ETH 4H) before live deployment — they share the Supertrend indicator.

## Deployment Recommendation
Ready for paper trading. Suggest standard 10× leverage, 10% risk/trade allocation. Low trade frequency (14 trades/year) means minimal slippage concern.

---
*Dev Report:* `dev_report/Trend/20260701_182_SupertrendEmaFilterStrategy_dev.md`
*Factor Card:* `factor_library/Trend_Momentum/20260527_supertrend_pro.md`
