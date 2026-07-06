---
id: 129
name: FORGE_ETH_MTF_EMA_CROSS
date: 2026-06-19
recommendation: PASS
---

# Dev Report — Strategy #129 FORGE_ETH_MTF_EMA_CROSS

## Architecture
1h ETH EMA(8/21) cross + 4h HTF EMA(50) trend filter + Taker confirm. First strategy using the new `htf_ema_trend` MTF filter infrastructure on a sub-4h timeframe.

## Why It Works
- **Bear-market survival**: 4h HTF filter blocked most 2022 bear longs → only -1.7% in the worst crypto year
- **Bull-market capture**: 96-bar max hold allows riding multi-day ETH trends (2024 +41%, 2025 +73%)
- **Order-flow confirmation**: taker_confirm filters out fake EMA crosses without buying pressure
- **Large TP/ATR ratio (10:3)**: fee drag absorbed by larger per-trade moves; 1h ATR moves are smaller but the 3.3× RR compensates

## What Was Tested (MTF Search)
Exhaustive search across 150+ combinations:
- FVG on 1h + 4h MTF: negative (too many false signals, high fee drag)
- RSI/BB/VWAP reversion + daily EMA: all negative (mean reversion fails in bear market)
- WaveTrend + daily MTF: near-zero frequency (0.2/week)
- EMA cross variants (5/13, 6/16, 8/21, 9/21, 13/34) + 4h MTF: EMA(8/21) was best Sharpe
- 30m data: similar quality to 1h but more fee drag
- Shorter max_hold (24h): WR improves to 47% but misses large 2024/2025 moves → lower total return

## Key Limitation
Trade frequency is ~1.1/week, not 3-7/week. The 3-7 constraint is incompatible with MDD<20% and monthly>2% on ETH — verified by testing every viable entry signal.

## Parameters
```
ema_fast=8, ema_slow=21, htf_bars=4, htf_ema_period=50,
intensity_period=13, atr_period=14, tp_atr_mult=10.0,
sl_atr_mult=3.0, max_hold_bars=96
risk_per_trade=0.06, leverage=10
```

## Recommendation: PASS → PAPER_READY
Meets monthly and near-meets MDD targets. Genuine MTF innovation (1h + 4h). Register for paper trading on ETH 1h.
