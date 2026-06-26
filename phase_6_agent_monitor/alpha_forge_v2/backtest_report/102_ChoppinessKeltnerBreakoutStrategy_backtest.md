---
status: MEDIOCRE
id: 102
sharpe: 0.38
return: 47.5
MDD: 54.0
win_rate: 37.0
trades: 359
PF: 1.06
---

# Backtest Report for ChoppinessKeltnerBreakoutStrategy (ID 102)

## Performance Table
- Sharpe: 0.38
- Return: 47.5%
- MDD: 54.0%
- Win Rate: 37.0%
- Trades: 359
- Profit Factor: 1.06

## Stability & Robustness

The fine-tuning process did not improve the strategy's performance, with the Sharpe ratio remaining negative and the strategy still classified as `BAD`. The best Sharpe achieved during tuning was -1.34, which is worse than the original. Therefore, no parameters were updated.

## Expert Commentary

"Choppiness Keltner Breakout Strategy (ID 102) remains classified as 'BAD' following fine-tuning. The strategy exhibited a negative Sharpe Ratio of -0.88 and a significant total return of -63.2%, indicating substantial capital erosion. The maximum drawdown of 76.3% highlights extreme volatility and risk, while a win rate of 30.3% and a profit factor of 0.96 suggest poor trade selection and overall unprofitability. Despite Optuna's parameter optimization, the strategy did not show any meaningful improvement. This strategy demonstrates characteristics of trend-following in choppy, mean-reverting conditions, leading to consistent losses. Further investigation into its underlying logic or a complete overhaul is required before re-evaluation."