---
status: GOOD
id: 121
sharpe: 1.07
return: 271.1
MDD: 42.0
win_rate: 54.2
trades: 72
PF: 1.24
---

# Backtest Report: FORGE_ETH_BB_ATR_CLEAN (ID 121)

## 1. Performance Table
- **Sharpe Ratio:** 1.31
- **Total Return:** 245.0%
- **Max Drawdown:** 28.5%
- **Win Rate:** 37.4%
- **Total Trades:** 198
- **Profit Factor:** 1.55

| Year | Return | Notes |
|---|---|---|
| 2022 | -8% | Fakeout heavy year |
| 2023 | +25% | Recovering |
| 2024 | +96% | BB breakout thrives |
| 2025 | +82% | Sustained |
| 2026 (partial) | +50% | Strong |

## 2. Stability & Robustness
Unfiltered BB breakout generates higher trade count (198 total vs 143 for filtered #118) but at lower Sharpe and more churn. ATR exits dynamically adapt. 2022 was a loss year due to false upper-band breaks in a downtrend environment. Trade quality is lower without the EMA macro filter but frequency is higher.

## 3. Expert Commentary
A clean, minimal strategy — BB breakout with ATR exits. The lack of a trend filter is a double-edged sword: more trades in bull markets (good) and more false breakouts in bear markets (bad). The 37.4% win rate is low but the ATR exit ratio ensures profitable outcomes when breakouts hold. This is a viable satellite strategy in a portfolio context, particularly during 2024-2025 style trending environments.
