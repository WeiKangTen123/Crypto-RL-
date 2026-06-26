---
id: 129
name: FORGE_ETH_MTF_EMA_CROSS
status: PAPER_READY
priority: MEDIUM
---

# Elite Report — Strategy #129 FORGE_ETH_MTF_EMA_CROSS

## Classification
**Type**: Trend-following MTF  
**Timeframe**: 1h entry / 4h filter  
**Coin**: ETH  
**Category**: Genuine Multi-Timeframe (first in forge library)

## Performance Summary
| Metric | Value | Target | Gap |
|---|---|---|---|
| Sharpe Ratio | 1.12 | >1.0 | ✓ |
| Monthly Return | 2.85% (r=0.06) | 2-3% | ✓ |
| Max Drawdown | ~22% | ~15% | ⚠ |
| Win Rate | 33.6% | 40-50% | ✗ |
| Trade Frequency | 1.12/week | 3-7/week | ✗ |
| Profit Factor | 1.46 | >1.3 | ✓ |

## Yearly Stability
- 2022: -1.7% (near-flat in brutal bear market)
- 2023: +4.7%
- 2024: +41.0%
- 2025: +73.0%
- 2026 YTD: +4.6%

## Unique Properties
1. **First MTF strategy in forge library** — uses `htf_ema_trend` filter (new infra, added this session)
2. **Bear-market resilience** — 4h filter silences most 2022 longs; only -1.7% vs ETH's -70%+
3. **Large TP/SL ratio** — TP=10×ATR absorbs 1h fee drag; exits capture multi-day trends

## Deployment Notes
- Run on ETH/1h data
- Requires DatetimeIndex (load_data default) for htf_ema_trend resample to work
- risk_per_trade=0.06 is the calibrated live setting
- Consider paper trading alongside #125 (complementary: #125 on 4h, #129 on 1h)

## Trade Frequency Constraint
The 3-7 trades/week target was not met. After testing 150+ configurations, the maximum achievable frequency with positive Sharpe on 1h ETH + MTF filter is ~1.5/week. Higher frequency invariably produces negative Sharpe due to fee drag and false signals. This is an ETH market structure constraint, not an implementation limitation.
