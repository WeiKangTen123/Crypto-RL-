---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: ema-ribbon-rsi-momentum
source: TradingView (Popular Setup)
status: IN_PROGRESS
tags:
- built
- backtested
timeframes: 1h, 4h
type: long-term
---
# EMA Ribbon Alignment + RSI Momentum

## Concept
A trend-following strategy that looks for the alignment of multiple EMAs (9, 21, 55) to confirm a strong trend, filtered by RSI to ensure momentum is not exhausted.

## Entry Conditions
- Long: EMA 9 > EMA 21 > EMA 55 AND RSI(14) > 50.
- Short: EMA 9 < EMA 21 < EMA 55 AND RSI(14) < 50.

## Exit Conditions
- Take profit: EMA 9 crosses back over EMA 21 or fixed R/R (2:1).
- Stop loss: Below/above EMA 55 or fixed % ATR.

## Key Indicators
- EMA (9, 21, 55)
- RSI (14)

## Expected Edge
Alignment of multiple time-horizon averages suggests a consensus in market direction. The RSI filter prevents entering "late" into overbought/oversold conditions.

## Data Requirements
- Columns needed: Close
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Works best in Trending regimes.
- Ribbon "fan-out" (increasing distance between EMAs) can be used as a strength indicator.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Trend_Momentum/20260526_dmi_adx_trend_strength]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]]
