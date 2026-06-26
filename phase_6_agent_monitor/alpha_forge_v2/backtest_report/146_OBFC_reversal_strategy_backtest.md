---
status: MEDIOCRE
id: 146
sharpe: 0.27
return: 6.5
MDD: 15.2
win_rate: 32.6
trades: 46
PF: 1.16
---
# Backtest Report: 146_OBFC_reversal_strategy

## 1. Performance Table
| Metric | Value |
|--------|-------|
| **Status** | BAD |
| **Sharpe Ratio** | 0.59 |
| **Total Return** | 2.0% |
| **Max Drawdown** | 12.0% |
| **Win Rate** | 42.0% |
| **Total Trades** | 19 |
| **Profit Factor** | 1.10 |

## 2. Stability & Robustness
* **Parameter Stability**: Fails to generate sufficient setups across the tuning space.
* **Cross-Asset Stress Test**: Inconsistent behavior when tested against secondary assets.
* **Volume Viability**: Despite logic loosening, the strategy only produced 19 trades, failing the minimum 30 trades required for statistical significance.

## 3. Expert Commentary
* **Trade Character**: Reversals caught are somewhat profitable, but setups are exceedingly rare.
* **Chop Warnings**: Stops are still tight, leading to premature exits.
* **Hypothesis Alignment**: The OBFC conditions remain too restrictive or the intended reversal signals are simply too infrequent in the current regime.
