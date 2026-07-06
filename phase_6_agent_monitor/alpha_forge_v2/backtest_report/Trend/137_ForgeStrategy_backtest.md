---
status: BAD
id: 137
sharpe: -6.04
return: -95.3
mdd: 95.6
win_rate: 27.8
trades: 1716
pf: 0.66
---
# Stage 03 Backtest Report: ForgeStrategy (Strategy ID 137)

## Performance Table
| Metric | Value |
|---|---|
| Sharpe | -6.04 |
| Total Return | -95.3% |
| Max Drawdown | 95.6% |
| Win Rate | 27.8% |
| Total Trades | 1716 |
| Profit Factor | 0.66 |

## Stability & Robustness
- **Validation Guard (Optuna Trials)**: Optuna fine-tuning did not yield any improvement over the baseline (best trial Sharpe remained -6.04). The strategy is highly sensitive to parameters and struggles to escape a negative performance regime, indicating a lack of a stable parameter space.
- **Cross-Asset Stress Test**: Due to failing baseline performance on BTC, cross-asset verification was bypassed to prevent unnecessary compute. The factor does not present viable alpha on the primary asset.
- **Hypothesis Verification**: The Williams %R reversion entry combined with a high-timeframe Supertrend filter on the 15m timeframe is rejected. The strategy triggers excessive trades (1,716 trades), resulting in significant fee drag and a deep drawdown of 95.6%, confirming that the filter is insufficient to prevent trading in unfavorable regimes.

## Expert Commentary
- **Trade Character**: The strategy displays a high frequency of trades with a very low win rate (27.8%), suffering from persistent fee friction and a negative profit expectancy. The entry rule fails to isolate genuine mean-reversion pivots.
- **Chop Warnings**: Highly vulnerable to sideways and choppy markets. The HTF Supertrend filter is unable to successfully filter out false reversion signals during consolidating or trending ranges, leading to capital erosion.
- **Hypothesis Alignment**: Strongly misaligned with the intended reversion behavior. Williams %R Reversion on the 15m TF is heavily impacted by market noise and short-term trends, leading to a catastrophic drawdown.
