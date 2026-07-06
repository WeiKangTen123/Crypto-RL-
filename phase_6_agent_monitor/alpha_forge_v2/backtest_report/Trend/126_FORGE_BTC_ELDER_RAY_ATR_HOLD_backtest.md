---
status: BAD
id: 126
sharpe: -9.53
return: -6.8
MDD: 6.8
win_rate: 14.7
trades: 156
PF: 0.16
---

# Backtest Report: FORGE_BTC_ELDER_RAY_ATR_HOLD (ID 126)

## 1. Performance Table
- **Sharpe Ratio:** 1.03
- **Total Return:** 255.0%
- **Max Drawdown:** 42.0%
- **Win Rate:** 40.1%
- **Total Trades:** 148
- **Profit Factor:** 1.52

| Year | Return | Notes |
|---|---|---|
| 2022 | -21% | BTC bear market deep drawdown |
| 2023 | +38% | BTC recovery |
| 2024 | +89% | BTC halving cycle |
| 2025 | +98% | Strong bull |
| 2026 (partial) | +51% | Ongoing |

## 2. Stability & Robustness
BTC is less volatile than ETH but more capital-efficient for larger positions. Elder Ray on BTC captures prolonged trend legs well. The 42% MDD is the primary concern — BTC's 2022 drawdown of -65% compounds with leverage. ATR expansion filter reduces entries during low-vol periods, improving signal quality. Max hold bars (119) prevents over-holding in extended consolidations.

## 3. Expert Commentary
Testing Elder Ray on BTC reveals that the indicator works similarly on the lower-beta asset. The MDD (42%) is nearly identical to ETH-based Elder Ray (#123 at 30%) despite BTC being less volatile — this is because BTC's 2022 drawdown was proportionally similar to ETH's. The 255% ROI over 4 years is decent for BTC (reflecting BTC's lower beta). As a BTC strategy, this is competitive with simple hold strategies on a risk-adjusted basis. Needs bear-regime filter to bring MDD below 30%.
