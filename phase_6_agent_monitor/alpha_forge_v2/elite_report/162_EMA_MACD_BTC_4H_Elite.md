---
strategy_id: 162
name: FORGE_EMA_MACD_BTC_4H
grade: ELITE
sharpe: 1.42
total_return: 144.4%
trades: 121
status: STRESS_TEST
---

# Stage 04: Market Fit Memo - EMA MACD Cross (BTC, 4H)

## Executive Summary
After a comprehensive 200-trial Optuna fine-tuning run by the `crypto-strategy-tuner` agent, the baseline `ema_macd_cross` strategy on the BTC 4H timeframe has been upgraded from a negative Sharpe ratio to an ELITE grade (Sharpe 1.42). 

## Tuning Analysis
- **Entry Logic:** Fast EMA (30) crossing Slow EMA (200), aligned with MACD confirmation (30, 88, 17).
- **Exit Logic:** ATR Trailing Stop (14 period). TP Multiplier: 3.475, SL Multiplier: 1.897.
- **Why it worked:** The baseline parameters (EMA 5/20) were far too fast, resulting in whipsaw destruction. The tuner discovered that extending the lookbacks into macroscopic trends (EMA 30/200 and MACD 30/88) filters out the chop and effectively captures the major BTC macro moves on the 4H chart.

## Next Steps
Proceeding to STRESS_TEST and Walk-Forward Optimization (WFO) to ensure this parameter set is not overfitted.
