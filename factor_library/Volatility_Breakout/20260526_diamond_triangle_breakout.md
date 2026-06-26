---
coins: BTC, ETH, SOL
interest: High
name: diamond-triangle-breakout
source: TradingView / General Quant Research
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: short-term
---
# Diamond Triangle Breakout

## Concept
Identifies geometric consolidation patterns (diamonds and triangles) and trades the breakout. The edge comes from using ATR-based dynamic trailing stops to handle crypto's high volatility.

## Entry Conditions
- Price consolidation within contracting Bollinger Bands (Squeeze).
- Breakout above/below the consolidation range with a Volume spike (Volume > 1.5x Moving Average of Volume).
- ADX > 25 (confirming strength of the breakout).

## Exit Conditions
- Take profit: ATR-based trailing stop (e.g., 3x ATR).
- Stop loss: 1.5x ATR from entry.

## Key Indicators
- Bollinger Bands (20, 2)
- ATR (14)
- ADX (14)
- Volume MA (20)

## Expected Edge
Consolidation phases often precede large directional moves. ATR trailing allows capturing the majority of a trend while protecting capital.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Requires a "squeeze" detection logic (BB width).
- Breakout must be confirmed by volume to avoid bull/bear traps.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Volatility_Breakout/bb_squeeze_breakout]] · [[Volatility_Breakout/20260527_avso_momentum]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260528_zero_lag_trend_speed_momentum]]
