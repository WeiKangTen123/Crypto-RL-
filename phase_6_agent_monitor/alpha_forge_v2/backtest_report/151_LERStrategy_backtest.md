---
status: BAD
id: 151
sharpe: -0.42
return: -30.2
MDD: 45.0
win_rate: 34.2
trades: 152
PF: 0.85
---
# Stage 03 Backtest Report: 151 (LERStrategy)

## 1. Performance Table
| Metric | Value |
|--------|-------|
| Sharpe | 0.16 |
| Return | -0.7% |
| MDD | 39.3% |
| Win Rate | 38.8% |
| Trades | 366 |
| Profit Factor | N/A |

## 2. Stability & Robustness
- **Stability**: Poor parameter robustness. The strategy fails to maintain profitability.
- **Robustness**: Reverting liquidity exhaustion without stronger trend context leads to high drawdown.

## 3. Expert Commentary
- **Trade Character**: High frequency (366 trades) but highly inefficient.
- **Chop Warnings**: Heavy chop during ranging markets causing bleed.
- **Hypothesis Alignment**: Fails to capture the intended edge.
