---
status: BAD
id: 198
sharpe: -0.49
return: -52.41
MDD: 73.12
win_rate: 31.50
trades: 852
PF: 0.81
---

# Backtest Report: 198_VolumeFOMORank_backtest

## 1. Performance Table
| Metric | Value |
| :--- | :--- |
| **Total Return** | -52.41% |
| **Sharpe Ratio** | -0.49 |
| **Max Drawdown** | 73.12% |
| **Win Rate** | 31.50% |
| **Total Trades** | 852 |
| **Profit Factor** | 0.81 |

## 2. Stability & Robustness
- **Status**: BAD. Strongly negative Sharpe and massive drawdown.
- **Multi-Coin Execution**: Validated. Ranks Pearson correlation of Volume vs Price across 5 assets.
- **Parameter Sensitivity**: Untuned baseline using a 14-bar rolling window for correlation.

## 3. Expert Commentary
- **Trade Character**: The strategy assumes that highly correlated volume and price spikes are exhaustive FOMO events that should be faded (shorted). The deep negative return proves the exact opposite: in crypto, volume-backed price spikes are **structural trend confirmations**, not exhaustions. Fading them is extremely dangerous.
- **Hypothesis Alignment**: Fading the Kimchi Premium/FOMO proxy is invalid as a baseline. The strategy must be inverted to a **momentum-following** regime.
- **Next Steps**: Optuna tuning can naturally discover the inversion by flipping the signal signs, or exploring if longer correlation windows (e.g., 28 bars) provide the actual exhaustion signals.
