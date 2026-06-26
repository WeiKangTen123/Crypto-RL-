---
status: BAD
id: 147
sharpe: -0.66
return: -27.2
MDD: 39.8
win_rate: 38.7
trades: 31
PF: 0.55
---
# Backtest Report: 147_HVE_reversion_strategy

## 1. Performance Table
| Metric | Value |
|--------|-------|
| **Status** | BAD |
| **Sharpe Ratio** | -0.36 |
| **Total Return** | -1.5% |
| **Max Drawdown** | 11.5% |
| **Win Rate** | 35.0% |
| **Total Trades** | 9 |
| **Profit Factor** | 0.85 |

## 2. Stability & Robustness
* **Parameter Stability**: Continues to yield negative performance even with loosened constraints.
* **Cross-Asset Stress Test**: Shows negative expectancy across alternative data sets.
* **Volume Viability**: Remains starved of trades (9 trades), indicating HVE (High Volatility Extremes) mean reversion is not a viable isolated trigger.

## 3. Expert Commentary
* **Trade Character**: Taking entries against strong momentum with poor outcomes.
* **Chop Warnings**: Highly susceptible to strong directional trends.
* **Hypothesis Alignment**: The mean reversion hypothesis during extreme volatility is completely invalidated by the data.
