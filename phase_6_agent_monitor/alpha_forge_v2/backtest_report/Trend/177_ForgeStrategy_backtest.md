---
status: MEDIOCRE
id: 177
sharpe: 1.23
return: 421.01
mdd: 38.23
win_rate: 15.28
trades: 288
pf: 1.48
---
# Stage 03 Backtest Report: FORGE_EMA_MACD_XRP_4H (ID 177)

## Performance Table
| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | 1.23 |
| **Total Return** | 421.01% |
| **Max Drawdown (MDD)** | 38.23% |
| **Win Rate** | 15.28% |
| **Total Trades** | 288 |
| **Profit Factor (PF)** | 1.48 |

## Stability & Robustness

### 1. Parameter Stability Test
Parameter stability checks were performed by perturbing the primary tunable parameters by ±10%.
- **ema_fast**: Perturbing from 7 to 6 resulted in Sharpe `1.08`. Perturbing to 8 resulted in Sharpe `1.07`.
- **ema_slow**: Perturbing from 148 to 133 resulted in Sharpe `0.59` (Performance crash!). Perturbing to 163 resulted in Sharpe `1.03`.
- **macd_fast**: Perturbing from 29 to 26 resulted in Sharpe `0.96`. Perturbing to 32 resulted in Sharpe `0.97`.
- **macd_slow**: Perturbing from 100 to 90 resulted in Sharpe `1.15`. Perturbing to 110 resulted in Sharpe `1.04`.
- **macd_signal**: Perturbing from 3 to 3 yielded Sharpe `1.23`.
- **tp_atr_mult**: Perturbing from 4.3814 to 3.9433 resulted in Sharpe `1.10`. Perturbing to 4.8195 resulted in Sharpe `1.12`.
- **sl_atr_mult**: Perturbing from 0.5276 to 0.4748 resulted in Sharpe `1.32`. Perturbing to 0.5804 resulted in Sharpe `1.11`.
- **atr_period**: Perturbing from 8 to 7 resulted in Sharpe `1.20`. Perturbing to 9 resulted in Sharpe `1.18`.
- **Verdict**: **FAILED**. The strategy exhibits parameter fragility. A 10% reduction in `ema_slow` (from 148 to 133) crashes the Sharpe ratio to `0.59` (more than a 50% decay from the baseline of `1.23`).

### 2. Cross-Asset Stress Test
- **ETH (4h)**: Sharpe `0.39` | 271 trades | Total Return `29.13%` | Max Drawdown `48.49%`
- **BTC (4h)**: Sharpe `-0.48` | 290 trades | Total Return `-37.42%` | Max Drawdown `55.69%`
- **Verdict**: **FAILED**. The strategy does not show global validity. While it maintains a weak positive edge on ETH, it performs poorly on BTC (Sharpe `-0.48`), suggesting the parameter set is highly overfit to the price dynamics of XRP.

## Expert Commentary

### Trade Character
With 288 trades over the test period, this strategy is moderately active (approx. 7 trades per month). It has a low win rate of 15.28% but compensates with a high average profit per winning trade (profit factor of 1.48), typical of trend-following breakout or crossover strategies using tight stop losses (`sl_atr_mult` of 0.53) and wide take profit targets (`tp_atr_mult` of 4.38).

### Chop Warnings
As a pure EMA and MACD crossover model, the strategy is highly vulnerable to whipsaws in sideways/consolidation regimes. In trendless markets, the crossover signals will trigger repeatedly during range boundaries, leading to a succession of losses before a clean trend is caught.

### Hypothesis Alignment
The original hypothesis predicted that combining fast and slow EMA crossovers with MACD filters would capture strong directional trends on XRP. The optimized results on XRP show a strong baseline Sharpe of 1.23. However, the extreme sensitivity to `ema_slow` and the negative performance on BTC confirm that the alpha is fragile and asset-specific rather than a robust market truth. It is classified as MEDIOCRE due to parameter stability issues and should not be deployed in production without additional macro filtering or wider parameter optimization.
