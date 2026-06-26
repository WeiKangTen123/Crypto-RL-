---
status: MEDIOCRE
id: 84
sharpe: 0.02
return: -0.2
MDD: 11.1
win_rate: 44.2
trades: 43
PF: 1.0
---
# Backtest Report: Strategy 84 (NowoIchimokuMTFStrategy)

## Performance Table
- Sharpe: 0.02
- Return: -0.2%
- MDD: 11.1%
- Win Rate: 44.2%
- Trades: 43
- Profit Factor: 1.0

## Stability & Robustness
The parameter stability test indicates extreme fragility. The strategy shows significant performance degradation after tuning (original Sharpe 0.33, best Sharpe -19.01).

## Expert Commentary
The strategy shows catastrophic failure in the tuned regime. The high trade count (9934) suggests extreme over-trading and likely overfitting in the tuning process. Recommend move to GRAVEYARD.
