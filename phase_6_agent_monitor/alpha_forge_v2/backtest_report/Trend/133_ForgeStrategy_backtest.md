---
status: BAD
id: 133
sharpe: -5.58
return: -6.4
mdd: 6.6
win_rate: 13.7
trades: 124
pf: 0.22
---
# Stage 03 Backtest Report: ForgeStrategy (Strategy ID 133)

## Performance Table
| Metric | Value |
|---|---|
| Sharpe | -5.58 |
| Total Return | -6.4% |
| Max Drawdown | 6.6% |
| Win Rate | 13.7% |
| Total Trades | 124 |
| Profit Factor | 0.22 |

## Stability & Robustness
- **Validation Guard (Optuna Trials)**: Optuna fine-tuning was executed but did not yield any improvement over the baseline (best trial Sharpe was -6.31 vs. baseline Sharpe of -5.58). The strategy is highly sensitive to parameters and cannot escape a negative performance regime, indicating a lack of a stable parameter space.
- **Cross-Asset Stress Test**: Due to the baseline Sharpe on the primary asset (BTC) being deeply negative (-5.58), cross-asset validation was bypassed to prevent unnecessary compute. The factor does not present viable alpha on the primary asset.
- **Hypothesis Verification**: The strategy's hypothesis was that BTC 5m taker buy intensity momentum entry, filtered by 4H HTF EMA trend and ATR expansion, could capture short-term breakout momentum. The results disprove the hypothesis: the entry signals are extremely noisy, leading to a very low win rate of 13.7% and a profit factor of 0.22 over 124 trades, showing no viable edge.

## Expert Commentary
- **Trade Character**: The strategy exhibits extremely low accuracy (13.7% win rate) with high transaction fee drag on 5m bars. The entry rule fails to distinguish between true breakout momentum and local market noise.
- **Chop Warnings**: Highly vulnerable to sideways and choppy markets on the 5m timeframe. The 4H HTF EMA trend filter is too laggy to protect against entries at local range tops/bottoms, leading to continuous capital erosion.
- **Hypothesis Alignment**: Strongly misaligned. While taker buy momentum indicates short-term order book activity, using it as a direct momentum entry on a 5m timeframe without a fast regime filter results in overtrading and high fee friction.
