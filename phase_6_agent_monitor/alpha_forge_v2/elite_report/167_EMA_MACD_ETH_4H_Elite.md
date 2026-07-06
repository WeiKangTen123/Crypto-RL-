---
strategy_id: 167
name: FORGE_EMA_MACD_ETH_4H
grade: ELITE
sharpe: 1.60
total_return: 513.6%
trades: 164
status: STRESS_TEST
---

# Stage 04: Market Fit Memo - EMA MACD Cross (ETH, 4H)

## Executive Summary
After 400 trials of Optuna fine-tuning, the EMA+MACD crossover strategy for ETH on the 4H timeframe was completely salvaged. Originally generating a negative Sharpe ratio, the tuned model now boasts a spectacular Sharpe Ratio of 1.60, returning 513.6% over 164 trades, elevating it to ELITE status.

## Tuning Analysis
- **Entry Logic:** Fast EMA (8) crossing Slow EMA (81), with MACD confirmation (30, 96, 20).
- **Exit Logic:** ATR Trailing Stop (26 period). TP Multiplier: 6.921, SL Multiplier: 1.151.
- **Why it worked:** The optimizer widened the MACD lookback significantly (30/96) to filter out the noise typical of ETH's 4H chart, while pairing it with an incredibly aggressive Take-Profit multiplier (6.9x ATR) to ensure that winning trades stay open during macro bull rallies.

## Next Steps
This strategy will immediately enter Phase 6 STRESS_TEST for out-of-sample Walk-Forward Optimization to ensure parameter stability.
