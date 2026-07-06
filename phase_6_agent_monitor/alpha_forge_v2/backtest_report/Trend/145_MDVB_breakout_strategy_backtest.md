---
status: MEDIOCRE
id: 145
sharpe: 0.23
return: 8.2
MDD: 39.8
win_rate: 34.2
trades: 114
PF: 1.1
---
# Backtest Report: 145_MDVB_breakout_strategy

## 1. Performance Table
| Metric | Value |
|--------|-------|
| **Status** | MEDIOCRE |
| **Sharpe Ratio** | 0.34 |
| **Total Return** | 4.5% |
| **Max Drawdown** | 38.6% |
| **Win Rate** | 48.0% |
| **Total Trades** | 35 |
| **Profit Factor** | 1.15 |

## 2. Stability & Robustness
* **Parameter Stability**: Improved trade frequency after logic adjustments, but returns remain marginal relative to risk.
* **Cross-Asset Stress Test**: Highly volatile across altcoins, indicating lack of robustness.
* **Volume Viability**: Cleared the trade frequency hurdle (>30 trades), but the excessive drawdown (38.6%) makes it unsuitable for production.

## 3. Expert Commentary
* **Trade Character**: Captures some genuine breakouts but gets frequently whipped out during consolidations.
* **Chop Warnings**: Severe drawdown indicates a major vulnerability to regime shifts or false breakouts.
* **Hypothesis Alignment**: Partially aligned. Breakouts occur, but the risk-reward ratio is insufficient to overcome the drawdowns.
