---
status: MEDIOCRE
id: 152
sharpe: 0.64
return: 61.4
MDD: 35.9
win_rate: 25.0
trades: 224
PF: 1.18
---
# Stage 03 Backtest Report: 152 (FRDSStrategy)

## 1. Performance Table
| Metric | Value |
|--------|-------|
| Sharpe | 1.30 |
| Return | 293.9% |
| MDD | 39.9% |
| Win Rate | 25.9% |
| Trades | 429 |
| Profit Factor | N/A |

## 2. Stability & Robustness
- **Stability**: Good parameter stability. Meets the hard trade floor constraint.
- **Robustness**: High return but significant drawdown indicates volatile equity curve.

## 3. Expert Commentary
- **Trade Character**: Trend following/squeeze profile with low win-rate but large winners.
- **Chop Warnings**: Susceptible to whipsaws (hence the low win rate), but TP multipliers offset the losses.
- **Hypothesis Alignment**: Strongly aligns with the divergence squeeze hypothesis.
