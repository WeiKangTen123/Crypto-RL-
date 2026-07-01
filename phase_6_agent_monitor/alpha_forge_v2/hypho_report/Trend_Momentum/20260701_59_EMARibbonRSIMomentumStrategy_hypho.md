# Hypothesis Report — EMA Ribbon RSI Momentum
**Date:** 2026-07-01 | **Strategy ID:** 59 | **Class:** EMARibbonRSIMomentumStrategy

---

## Alpha Hypothesis

**Core Idea:** When three EMAs of different periods (fast=9, medium=21, slow=55) are perfectly ordered in the same direction, all time horizons agree on trend direction. The RSI filter prevents entries when momentum is already exhausted (overbought/oversold). Together, these form a high-confidence trend entry.

**Mathematical Formulation:**
```
EMA_f = EMA(Close, ema_fast=9)
EMA_m = EMA(Close, ema_med=21)
EMA_s = EMA(Close, ema_slow=55)

Long  entry: EMA_f > EMA_m > EMA_s  AND  RSI(14) > rsi_threshold(50)
             AND first bar of alignment (EMA_f crossed above EMA_m on this bar)
Short entry: EMA_f < EMA_m < EMA_s  AND  RSI(14) < (100 - rsi_threshold)
             AND first bar of alignment

Exit (signal): EMA_f crosses back over EMA_m (trend breakdown)
Exit (risk):   ATR SL/TP
```

**Entry Trigger:** `require_crossover=True` — only enter on the first bar of full ribbon alignment, not every bar while aligned. This avoids late entries deep into the trend.

---

## Source & Provenance
- **Source:** TradingView (widely used institutional setup)
- **Originality:** Crossover-trigger entry + RSI momentum gate combination

## Expected Edge
Triple EMA alignment eliminates most noise signals. The crossover trigger ensures entry at the start of the trend consensus rather than mid-trend. RSI gate prevents catching a trend that's already peaking.

## Hypothesised Regime
- **Best:** Strong directional trending (low BBW, high ADX)
- **Worst:** Whipsaw / ranging markets — triple alignment forms and breaks frequently

## Risk Flags
- EMA 55 lags significantly — entries can be 10-20 bars after the actual trend start
- In ranging markets, EMA 9/21/55 alignments are short-lived → many small losses

---
*Factor Card:* `factor_library/Trend_Momentum/20260527_ema_ribbon_rsi_momentum.md`
