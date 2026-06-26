---
status: BAD
id: 98
sharpe: -0.24
return: -49.3
mdd: 67.2
win_rate: 9.2
trades: 358
pf: 0.9
---
# Backtest Report: VWAPATRReversionStrategy

## 1. Performance Table
| Metric | Value |
|---|---|
| Sharpe Ratio | 0.97 |
| Total Return | 4.4% |
| Max Drawdown | 1.3% |
| Win Rate | 3.9% |
| Total Trades | 52 |
| Profit Factor | 0.71 |

## 2. Stability & Robustness
The strategy underwent parameter stability testing via Optuna. Fine-tuning did not improve the baseline performance. Although the drawdown is minimal (1.3%), the win rate is abysmal (3.9%) and the profit factor is unprofitable (0.71).

## 3. Expert Commentary
- **Trade Character:** Only winning 3.9% of the time implies that almost every entry is a loser. The positive Sharpe is misleading due to the low total return and potential anomaly in volatility scaling.
- **Chop Warnings:** The strategy is fundamentally losing on every trade. The VWAP reversion logic is likely entering too early against strong momentum.
- **Hypothesis Alignment:** The hypothesis fails empirical validation. The reversion edge is absent. This strategy should be discarded unless the exit logic is completely overhauled.
