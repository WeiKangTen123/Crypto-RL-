---
status: BAD
id: 138
sharpe: -6.16
return: -22.9
mdd: 23.4
win_rate: 13.3
trades: 128
pf: 0.23
---
# Stage 03 Backtest Report: ForgeStrategy (Strategy ID 138)

## Performance Table
| Metric | Value |
|---|---|
| Sharpe | -6.16 |
| Total Return | -22.9% |
| Max Drawdown | 23.4% |
| Win Rate | 13.3% |
| Total Trades | 128 |
| Profit Factor | 0.23 |

## Stability & Robustness
- **Validation Guard (Optuna Trials)**: Optuna fine-tuning did not yield a positive Sharpe ratio (best trial Sharpe was -6.32 vs baseline -6.16). The parameters are fragile, and optimizing them degrades the Sharpe ratio further, confirming extreme parameter sensitivity and lack of robustness.
- **Cross-Asset Stress Test**: Due to failing baseline performance on BTC, cross-asset verification was bypassed to prevent unnecessary compute. The factor does not present viable alpha on the primary asset.
- **Hypothesis Verification**: The taker momentum hypothesis on the 5m timeframe is rejected. The entry mechanism generates high noise, resulting in a very low win rate (13.3%) and a profit factor of 0.23, which does not cover trading fee friction.

## Expert Commentary
- **Trade Character**: The strategy displays a high rate of false breakouts, suffering from continuous small losses. The entry rule fails to identify sustained momentum.
- **Chop Warnings**: Highly vulnerable to choppy regimes. The filters (`htf_ema_trend` and `atr_expansion`) fail to filter out consolidating periods.
- **Hypothesis Alignment**: Strongly misaligned with the intended trend-following behavior. Taker momentum on 5m is highly mean-reverting or noisy under current market dynamics.
