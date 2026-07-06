---
status: BAD
id: 140
sharpe: 0.27
return: 18.2
mdd: 27.9
win_rate: 21.1
trades: 38
pf: 1.20
---
# Stage 03 Backtest Report: RsiMeanReversionStrategy

## Performance Table
| Metric | Value |
| --- | --- |
| Sharpe Ratio | 0.27 |
| Total Return | 18.16% |
| Max Drawdown % | 27.92% |
| Win Rate | 21.05% |
| Total Trades | 38 |
| Profit Factor | 1.20 |

## Stability & Robustness
*   **Parameter Stability Test**: **FAILED**. Perturbations of ±10% in parameters cause significant performance drops:
    *   Increasing `rsi_period` from 30 to 33 drops the Sharpe Ratio to -0.05.
    *   Perturbing `rsi_oversold` to 29.61 drops the Sharpe Ratio to -0.31.
    *   Perturbing `rsi_overbought` to 71.81 drops the Sharpe Ratio to -0.40.
    *   Varying the `tp_multiplier` down to 5.39 or up to 6.59 collapses the Sharpe Ratio to 0.09 and 0.05 respectively.
    *   This indicates the optimized parameter set is a highly fragile peak and not robust.
*   **Cross-Asset Stress Test**: **FAILED**. Running the strategy on ETH/4h results in a Sharpe Ratio of -0.46, a negative return of -41.58%, and a maximum drawdown of 50.01% over 30 trades.

## Expert Commentary
*   **Trade Character**: The strategy has a low trade frequency (only 38 trades over 5 years on the 4h timeframe, averaging ~7.6 trades per year) and a low win rate of 21.1%. However, the profit factor of 1.20 is driven by a high payoff ratio (large average gains on the few winning trades compared to small losses on the stop-outs), utilizing a tight stop loss multiplier (0.88 ATR) and a very wide take profit multiplier (5.99 ATR).
*   **Chop Warnings**: Due to the wide take profit level (5.99 ATR) and lack of regime gating, the strategy is highly vulnerable to prolonged sideways chop where the price fails to reach the profit target and is eventually stopped out or suffers time decay.
*   **Hypothesis Alignment**: The initial hypothesis of simple RSI mean reversion is not confirmed. While the parameter tuning managed to extract a positive Sharpe on BTC (0.27 vs baseline -1.1), it is highly overfit to BTC's specific price path, fails to generalize to ETH, and collapses under minor parameter variations.
