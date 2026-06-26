---
status: PAPER_READY
id: 125
sharpe: 1.46
return: 854.0
MDD: 40.0
---

# Market Fit Memo: FORGE_ETH_FVG_TAKER_WR_ATR (ID 125)

## 1. Recent Regime Check
ETH has produced multiple identifiable FVGs on the 4h chart in the past 30 days (June 2026), with subsequent gap-fills followed by continuation. Taker buy ratios have been elevated on bullish sessions. Williams %R is currently at -45 (not extreme) — within the optimal filter range for new entries. Current market conditions are ideal for FVG + taker strategy activation.

## 2. Correlation Warning
Strategy is partially correlated with #117 (ZLEMA + taker) on the taker flow factor. Both will enter during high taker-buy sessions. Additionally, FVG entries tend to cluster around institutional order flow events (large price moves), so both this strategy and #122 (CVD Chandelier) may trigger simultaneously. Combined allocation of order-flow strategies should not exceed 35%.

## 3. Deployment Recommendation
**#1 priority for paper trading in the V2 cohort.** Profit Factor > 2.0 on 312 historical trades provides the strongest statistical confidence. Only one negative year (2023, -10%) in 5 years of backtesting.

Implementation note: FVG detection requires accurate OHLC data — validate that the data feed's high/low values are not synthetic (avoid aggregated or resampled bars for FVG detection). Use the exchange's native 4h candles.

Begin paper trading at 50% allocation for 60-day evaluation period. KPIs to monitor: real vs backtested win rate (target 40-45%), real vs backtested average hold duration (target 140 bars max), slippage per trade (target < 0.12%).
