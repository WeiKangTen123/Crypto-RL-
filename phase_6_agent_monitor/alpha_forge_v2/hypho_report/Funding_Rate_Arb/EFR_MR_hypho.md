# HYPOTHESIS REPORT: Extreme Funding Rate Mean Reversion (EFR-MR)
**Date**: 2026-06-24
**Target Metrics**: Monthly ROI 2-3%, MDD ~20%, Sharpe > 1.0, 1 trade every 2-3 days.

## 1. Core Hypothesis
By combining Extreme Funding Rate Z-Scores with Spot Order Book Imbalance, we can reliably capture basis convergence and mean reversion without getting run over by strong trends. The spot OBI serves as a necessary institutional gate.

## 2. Expected Behavior
- **Win Rate**: ~55-60%.
- **Drawdown**: Mitigated by the Spot OBI filter.
- **Frequency**: 4H timeframe yields ~10-15 signals per month across 5 coins.

## 3. Validation Criteria
- Backtest must show Sharpe >= 1.0.
- Must outperform standard MACD/RSI baselines by avoiding lagging entries.
