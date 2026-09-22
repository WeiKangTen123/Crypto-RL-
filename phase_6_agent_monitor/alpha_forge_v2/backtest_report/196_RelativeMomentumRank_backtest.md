---
status: BAD
id: 196
sharpe: 0.37
return: -56.20
MDD: 91.80
win_rate: 38.01
trades: 634
PF: 1.10
---

# Backtest Report: 196_RelativeMomentumRank_backtest

## 1. Performance Table
| Metric | Value |
| :--- | :--- |
| **Total Return** | -56.20% |
| **Sharpe Ratio** | 0.37 |
| **Max Drawdown** | 91.80% |
| **Win Rate** | 38.01% |
| **Total Trades** | 634 |
| **Profit Factor** | 1.10 |

## 2. Stability & Robustness
- **Status**: BAD. Max Drawdown exceeded the hard 85% limit (91.80%).
- **Multi-Coin Execution**: Validated. The strategy successfully executed cross-margin trades across 5 assets (BTC, ETH, BNB, SOL, XRP).
- **Parameter Sensitivity**: Untuned. This is the baseline execution.

## 3. Expert Commentary
- **Trade Character**: The positive expectancy combined with negative returns and high MDD suggests severe whipsaw during consolidation periods.
- **Hypothesis Alignment**: The momentum premise is partially validated by the profit factor > 1.0 and positive expectancy, indicating that when the trend holds, the ranking accurately captures rotation.
- **Next Steps**: Will require robust Optuna tuning to optimize the `roc_period`, `sl_pct`, and `tp_pct` to avoid false signals and limit the massive drawdown before it can be reconsidered for promotion.
