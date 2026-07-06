---
coins: BTC, ETH, SOL
interest: High
name: avso-momentum
source: Zeiierman (GitHub) / Pine Script Community
status: COMPLETED
tags:
- built
- backtested
timeframes: 1h, 4h
type: long-term
---
# Adaptive Volatility-Scaled Oscillator (AVSO) Momentum

## Concept
The AVSO is a momentum oscillator that dynamically adjusts its sensitivity based on market volatility. It uses a volatility factor to scale the momentum calculation, effectively filtering out low-volatility "noise" and highlighting strong, high-conviction moves.

## Entry Conditions
- Buy: AVSO crosses above the zero line AND current volatility (ATR-based) is above a dynamic threshold.
- Sell: AVSO crosses below the zero line AND current volatility is above a dynamic threshold.

## Exit Conditions
- Take profit: Volatility-based exit or opposing AVSO cross.
- Stop loss: ATR-based trailing stop (2.5 * ATR).

## Key Indicators
- AVSO (length=14, smoothing=3)
- Volatility Threshold (ATR-based)

## Expected Edge
Crypto markets exhibit extreme regime shifts between high-volatility trends and low-volatility ranges. Standard oscillators often generate false signals in ranges. AVSO's volatility scaling provides a natural filter for these regimes.

## Data Requirements
- Columns needed: Close, High, Low, Volume
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Requires calculation of a volatility factor, often a ratio of current ATR to a long-term ATR average.
- Smoothing is critical to avoid whip-saws at the zero-line.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Volatility_Breakout/bb_squeeze_breakout]] · [[Volatility_Breakout/20260526_diamond_triangle_breakout]] · [[Trend_Momentum/20260527_supertrend_pro]] · [[Trend_Momentum/20260526_supertrend_pro_volatility]] · [[Trend_Momentum/20260526_supertrend_atr_momentum]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
