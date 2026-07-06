---
status: BAD
id: 111
sharpe: -0.23
return: -12.6
mdd: 20.7
win_rate: 29.8
trades: 84
pf: 0.86
---
# Stage 03 Backtest Report: ETHMomentumSqueezeStrategy (ID 111)

## Performance Table
| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | -0.23 |
| **Total Return** | -12.61% |
| **Max Drawdown (MDD)** | 20.74% |
| **Win Rate** | 29.76% |
| **Total Trades** | 84 |
| **Profit Factor (PF)** | 0.86 |

## Stability & Robustness

### 1. Parameter Stability Test
Parameter stability checks were performed by perturbing the primary tunable parameters by ±10%.
- **bb_period**: Perturbing from 21 to 19 resulted in Sharpe `-0.25`. Perturbing to 23 resulted in Sharpe `-0.06`.
- **bb_std**: Perturbing from 2.9261 to 2.6335 resulted in Sharpe `0.19`. Perturbing to 3.2187 resulted in Sharpe `-0.13`.
- **Other Parameters**: Perturbations of `intensity_period`, `intensity_std`, `taker_threshold`, `sl_atr_mult`, `tp_atr_mult`, and `max_hold_bars` yielded exactly the baseline Sharpe of `-0.23`.
- **Verdict**: Performance is stable but consistently unprofitable. There is no evidence of parameter fragility causing a sudden crash from a high peak; the strategy simply lacks an edge.

### 2. Cross-Asset Stress Test
- **BTC (1h)**: Sharpe `-0.11` | 95 trades | Total Return `-6.47%` | Max Drawdown `23.61%`
- **SOL (1h)**: Sharpe `-0.26` | 37 trades | Total Return `-12.95%` | Max Drawdown `34.68%`
- **Verdict**: Failed. The strategy shows globally negative performance across all major assets.

## Expert Commentary

### Trade Character
With a total of 84 trades over the 5.4-year backtest period, the strategy exhibits low trade frequency (~1.3 trades per month). It aims for higher payout trades (win rate 29.8%) but is severely dragged down by low average trade profitability, leading to a profit factor of 0.86.

### Chop Warnings
As a Bollinger Band and Keltner Channel squeeze system, this strategy is highly vulnerable to consolidation periods. Squeezes regularly trigger entries on minor volatility expansions that immediately reverse, resulting in frequent whipsaws and losses.

### Hypothesis Alignment
The original hypothesis predicted that combining Bollinger and Keltner squeeze indicators with taker buy/sell intensity filters would capture strong breakouts on ETH. However, the data proves otherwise. Squeeze signals without macro volume filters or regime-awareness fail to capture clean trends and instead suffer from constant false breakouts, making this strategy unsuitable for deployment.
