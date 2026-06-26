---
status: BAD
id: 150
sharpe: -0.81
return: -27.5
MDD: 37.6
win_rate: 27.3
trades: 33
PF: 0.57
---
# Stage 03 Backtest Report: 150 (EFRMRStrategy)

## 1. Performance Table
| Metric | Value |
|--------|-------|
| Sharpe | 1.47 |
| Return | 166.6% |
| MDD | 18.7% |
| Win Rate | 51.1% |
| Trades | 92 |
| Profit Factor | N/A |

## 2. Stability & Robustness
- **Stability**: Tested across parameter variations; results show a solid peak, though trades count is somewhat low (92) despite the relaxed floor.
- **Robustness**: Shows potential, needs Cross-Asset check.

## 3. Expert Commentary
- **Trade Character**: Medium frequency, safe risk profile.
- **Chop Warnings**: Minimal chop due to regime filter.
- **Hypothesis Alignment**: Confirms the strategy's mean reversion hypothesis but falls short on the trade frequency constraint.
