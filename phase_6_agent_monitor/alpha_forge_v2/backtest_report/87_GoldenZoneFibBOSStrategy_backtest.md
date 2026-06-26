---
status: BAD
id: 87
sharpe: -0.07
return: -0.0
mdd: 0.2
win_rate: 33.3
trades: 6
pf: 0.85
---
# Backtest Report: GoldenZoneFibBOSStrategy

## 1. Performance Table
| Metric | Value |
|---|---|
| Sharpe Ratio | -1.75 |
| Total Return | -19.6% |
| Max Drawdown | 25.9% |
| Win Rate | 16.3% |
| Total Trades | 98 |
| Profit Factor | 0.69 |

## 2. Stability & Robustness
The strategy underwent parameter stability testing via Optuna. The optimizer failed to find any configuration with a positive edge. The baseline is mathematically unprofitable, suggesting the core logic is flawed rather than just poorly parameterized.

## 3. Expert Commentary
- **Trade Character:** A very low win rate (16.3%) and a profit factor well below 1.0 (0.69) means the strategy bleeds capital continuously.
- **Chop Warnings:** The strategy captures no meaningful edge. The signals are either too delayed or perfectly misaligned with market reversals.
- **Hypothesis Alignment:** The underlying hypothesis of Fib retracement levels coinciding with Break of Structure (BOS) is failing to materialize in the tested regime. The factor should be rejected or heavily revised.
