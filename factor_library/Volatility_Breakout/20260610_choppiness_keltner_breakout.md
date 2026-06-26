---
status: PENDING
confidence: HIGH
class: Volatility_Breakout
author: alpha-researcher
tags:
  - Choppiness Index
  - Keltner Channel
  - Trend Breakout
---

# Choppiness Index & Keltner Channel Breakout

## Concept
The Choppiness Index (CHOP) determines if the market is choppy (trading sideways) or trending (trading within a trend in either direction). Values above 61.8 indicate high choppiness (consolidation), while values below 38.2 indicate a strong trend. 
When combined with Keltner Channel breakouts, it filters out false breakouts that occur in choppy regimes, only taking breakouts when CHOP indicates a trending regime is starting (CHOP dropping from high values).

## Math/Logic
- **Choppiness Index (CHOP)**:
  `100 * LOG10( SUM(ATR(1), n) / ( MaxHi(n) - MinLo(n) ) ) / LOG10(n)`
  Standard period `n` = 14.
- **Keltner Channel**:
  `Mid = EMA(Close, 20)`
  `Upper = Mid + 2 * ATR(20)`
  `Lower = Mid - 2 * ATR(20)`
- **Signal**:
  - `Long`: Close > Upper Keltner Channel AND CHOP < 50 AND CHOP is falling.
  - `Short`: Close < Lower Keltner Channel AND CHOP < 50 AND CHOP is falling.

## Market Regime Notes
This factor heavily penalizes high volatility mean-reverting environments and waits for a directional expansion.