---
status: BAD
id: 103
sharpe: 0.190
return: 3.8
mdd: 8.4
win_rate: 42.9
trades: 35
pf: 1.21
---
# Stage 03 Backtest Report: DynamicVWAPATRScalperStrategy

## Performance Table
| Metric | Value |
| --- | --- |
| Sharpe Ratio | 0.190 |
| Total Return | 3.8% |
| Max Drawdown | 8.4% |
| Win Rate | 42.9% |
| Total Trades | 35 |
| Profit Factor | 1.21 |

## Stability & Robustness
### Validation Guards summary:
- **Parameter Stability Test**: FAILED. Numerical parameters are highly fragile.
  - Perturbing `atr_period` to 9.0 (from 10) crashes Sharpe to -0.050.
  - Perturbing `atr_multiplier` by -10% (2.9165) drops Sharpe to -0.080, and by +10% (3.5647) drops Sharpe to -0.430.
  - Perturbing `rsi_oversold` to 30.7839 drops Sharpe to 0.090.
  - Perturbing `rsi_overbought` to 71.0466 drops Sharpe to -0.100.
  - Perturbing `vol_ma_period` to 28.0 drops Sharpe to 0.070.
  - Perturbing `vol_multiplier` to 2.6729 drops Sharpe to 0.050.
- **Cross-Asset Stress Test**: FAILED.
  - ETH (secondary asset) Sharpe is -0.500 over 29 trades with a return of -12.1%.
  - The alpha factor lacks global validity and is highly asset-specific to BTC.

## Expert Commentary
- **Trade Character**: The strategy functions as a conservative reversion model using a dynamic VWAP band coupled with ATR multipliers. On the 1-hour timeframe, it generated only 35 trades over a 5-year period. This low trade frequency indicates that signal generation is highly restrictive, limiting statistical significance and confirming that the strategy only participates in extreme outlier expansions.
- **Chop Warnings**: Under flat or sideways market conditions, this strategy remains inactive, avoiding false entries. However, the high sensitivity to the volume multiplier (`vol_multiplier`) and standard deviation bands means that a slight decline in regime volatility can lead to either total inactivity or a rash of false breakout-reversion signals. The lack of standard trend-filter resilience makes it vulnerable to extended, one-directional trends without quick mean reversion.
- **Hypothesis Alignment**: The original hypothesis predicted that price deviations from the VWAP during high-volume exhaustion points would mean-revert on the 1-hour timeframe. While the primary backtest on BTC shows a weak positive Sharpe ratio of 0.190 (improving on the baseline's -0.290), the severe underperformance on ETH (-0.500 Sharpe) and parameter fragility suggest that the model's parameters represent a fragile peak overfit to BTC historical price action.
