---
strategy_id: 172
name: FORGE_EMA_MACD_SOL_4H
grade: ELITE
sharpe: 1.93
total_return: 1529.8%
trades: 177
status: STRESS_TEST
---

# Stage 04: Market Fit Memo - EMA MACD Cross (SOL, 4H)

## Executive Summary
Following Optuna fine-tuning, the EMA+MACD crossover strategy for SOL on the 4H timeframe achieved an incredible Sharpe Ratio of 1.93, producing an extraordinary 1529.8% return across 177 trades. This upgrades the strategy to ELITE status.

## Tuning Analysis
- **Entry Logic:** Fast EMA (21) crossing Slow EMA (35), aligned with MACD confirmation (29, 87, 18).
- **Exit Logic:** ATR Trailing Stop (15 period). TP Multiplier: 4.894, SL Multiplier: 1.103.
- **Why it worked:** SOL experiences massive momentum super-cycles. The optimizer discovered that a moderately tight EMA crossover (21/35) coupled with a delayed, smoothed MACD (29/87/18) perfectly filters out false moves while locking into SOL's violent breakouts. The massive TP multiplier (4.89) allows the strategy to ride the entire wave.

## Next Steps
This strategy is highly promising. Moving to Phase 6 STRESS_TEST (Walk-Forward Optimization and Parameter Stability) to verify these metrics hold out of sample.
