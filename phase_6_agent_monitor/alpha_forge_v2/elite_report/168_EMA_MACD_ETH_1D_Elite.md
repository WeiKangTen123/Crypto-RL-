---
strategy_id: 168
name: FORGE_EMA_MACD_ETH_1D
grade: ELITE
sharpe: 1.21
total_return: 321.5%
trades: 33
status: STRESS_TEST
---

# Stage 04: Market Fit Memo - EMA MACD Cross (ETH, 1D)

## Executive Summary
After 400 trials of Optuna fine-tuning, the EMA+MACD crossover strategy for ETH on the 1D (Daily) timeframe has been dramatically improved. Moving from a barely-breakeven negative Sharpe (-0.06), it has surged to an ELITE grade with a Sharpe Ratio of 1.21, returning 321.5% across 33 high-quality macro trades.

## Tuning Analysis
- **Entry Logic:** Fast EMA (8) crossing Slow EMA (71), with MACD confirmation (28, 31, 9).
- **Exit Logic:** ATR Trailing Stop (9 period). TP Multiplier: 5.052, SL Multiplier: 1.218.
- **Why it worked:** The optimizer tuned the strategy into a pure macro-trend follower. By establishing a very fast MACD cross (28/31) heavily gated by a much slower macro EMA filter (8/71), the strategy successfully catches long, smooth trend cycles on the daily timeframe while avoiding false tops.

## Next Steps
This strategy will move to Phase 6 STRESS_TEST for Walk-Forward Optimization to verify its robustness against historical structural breaks.
