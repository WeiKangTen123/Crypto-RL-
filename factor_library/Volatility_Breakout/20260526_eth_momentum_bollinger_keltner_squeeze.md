---
coins: ETH
interest: High
name: ETH Momentum Bollinger Keltner Squeeze
source: TradingView (Popular Pine Script Collection)
status: IMPLEMENTED
tags:
- queued
- implemented
timeframes: 1h, 4h
type: mid-term
---
# ETH Momentum Bollinger Keltner Squeeze

## Concept
Uses the relationship between Bollinger Bands and Keltner Channels to identify periods of low volatility (squeeze) followed by explosive momentum breakouts.

## Entry Conditions
- Squeeze: Bollinger Bands (20, 2) are completely inside Keltner Channels (20, 1.5).
- Breakout: Price closes above the upper Bollinger Band AND Momentum (e.g., ADX > 25 or MACD Histogram > 0).
- Regime Filter: Price must be above 200 EMA for longs.

## Exit Conditions
- Take profit: ATR-based multiple or when Bollinger Bands begin to contract (slope of BB width turns negative).
- Stop loss: 2.5 * ATR or below the 20 EMA.

## Key Indicators
- Bollinger Bands (20, 2).
- Keltner Channels (20, 1.5).
- ADX (14) or MACD (12, 26, 9).
- EMA (200).

## Expected Edge
Capitalizes on the transition from low-volatility consolidation to high-volatility expansion, a common characteristic of Ethereum's price action.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume.
- Minimum timeframe: 1h.
- Minimum history: 2 years.

## Implementation Notes
- "Squeeze" detection is the core logic.
- ETH specific filters (like correlation with BTC or Gas fees) could be added but aren't required for the base version.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/Bollinger_Bands]] · [[_Concepts/EMA]]

**Related Factors:** [[Volatility_Breakout/bb_squeeze_breakout]] · [[Volatility_Breakout/20260527_avso_momentum]] · [[Volatility_Breakout/20260526_diamond_triangle_breakout]]
