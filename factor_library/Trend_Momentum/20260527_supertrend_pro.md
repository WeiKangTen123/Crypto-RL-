---
coins: BTC, ETH, SOL
interest: High
name: Supertrend Pro
source: Web research (refined from classic Supertrend)
status: QUEUED
tags:
- queued
timeframes: 4h, 1d
type: long-term
---
# Supertrend Pro

## Concept
A trend-following strategy that uses the Supertrend indicator but filters for macro trend direction using a 200-period EMA to avoid whipsaws in ranging markets.

## Entry Conditions
- Price is above 200-period EMA (Macro Bullish).
- Supertrend signal turns from Sell to Buy.

## Exit Conditions
- Take profit: ATR-based trailing stop or Supertrend flip.
- Stop loss: Supertrend line or fixed ATR multiple.

## Key Indicators
- Supertrend (10, 3.0)
- EMA (200)
- ATR (14) for volatility-adjusted stops

## Expected Edge
Reduces false signals in sideways markets by ensuring trades are only taken in the direction of the long-term trend.

## Data Requirements
- Columns needed: Open, High, Low, Close
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Non-repainting signals are critical.
- Needs careful handling of the 200 EMA warmup period.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/20260526_supertrend_pro_volatility]] · [[Trend_Momentum/20260526_supertrend_atr_momentum]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]] · [[Volatility_Breakout/20260527_avso_momentum]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]]
