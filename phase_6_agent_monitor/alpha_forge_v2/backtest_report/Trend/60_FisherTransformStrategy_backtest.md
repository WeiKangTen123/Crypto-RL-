---
status: BAD
id: 60
sharpe: -5.4
return: -100.0
mdd: 100.0
win_rate: 27.0
trades: 8729
pf: 0.87
---
# Stage 03 Backtest Report: FisherTransformStrategy (Strategy ID 60)

## Performance Table
| Metric | Value |
|---|---|
| Sharpe | -5.40 |
| Total Return | -100.0% |
| Max Drawdown | 100.0% |
| Win Rate | 27.0% |
| Total Trades | 8729 |
| Profit Factor | 0.87 |

## Stability & Robustness
- **Validation Guard (Optuna Trials)**: Optuna fine-tuning over 100 trials failed to restore profitability. The best parameters (`period`: 22) yielded a Sharpe of `-5.54`, compared to the baseline `-5.40` with `period: 16`. Since there is no parameter combination that yields positive returns or reduces trade frequency, this indicates a deeply flawed strategy design rather than poor tuning.
- **Cross-Asset Stress Test**: Run on secondary assets ETH and BTC. The strategy performs terribly across all assets:
  - ETH Sharpe: `-3.70` (8,631 trades, -100.0% return)
  - BTC Sharpe: `-5.40` (8,729 trades, -100.0% return)
  This shows the underlying alpha factor fails to establish any market edge and suffers from global invalidity.
- **Parameter Stability Test**: Perturbing the period parameter by ±10%:
  - Period 14: Sharpe = `-6.19`
  - Period 18: Sharpe = `-5.65`
  While the strategy does not technically "crash" (as it is already at the floor of -100% return), the performance remains highly hostile across the entire parameter space.
- **Hypothesis Verification**: The hypothesis that Fisher Transform peaks can isolate high-probability reversal turning points is rejected. Without additional volume, trend, or momentum filters, the raw Fisher Transform indicator generates excessive entry triggers (8,729 trades), leading to massive capital depletion via fee friction and spread.

## Expert Commentary
- **Trade Character**: Characterized by extremely high trade frequency (8,729 trades) and low win rate (27.0%). This high-frequency churn indicates that the strategy is responding to minor intra-bar volatility and market noise rather than significant turning points.
- **Chop Warnings**: Highly vulnerable to sideways consolidation. In a range-bound market, the Fisher Transform frequently crosses its signal thresholds, triggering back-to-back whipsaw losses.
- **Hypothesis Alignment**: Weak alignment with the theoretical edge of the Fisher Transform. The conversion to a normal distribution is distorted by fat-tailed crypto distributions, causing premature entries during strong momentum runs.
