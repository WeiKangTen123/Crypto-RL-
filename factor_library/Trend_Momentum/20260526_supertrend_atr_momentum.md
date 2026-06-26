---
coins: BTC, ETH, SOL
interest: High
name: supertrend-atr-momentum
source: Web Search (TradingView momentum trends 2024)
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: long-term
---
# SuperTrend ATR Momentum

## Concept
A regime-switching trend following strategy that uses SuperTrend for direction and ATR for dynamic position management, aiming to catch large breakouts during high-volatility regimes.

## Entry Conditions
- SuperTrend flips from bearish to bullish.
- ADX > 25 (indicating trending market).

## Exit Conditions
- Take profit: ATR based (e.g. 3x ATR).
- Stop loss: SuperTrend line or 1x ATR.

## Key Indicators
- SuperTrend (10, 3)
- ATR (14)
- ADX (14)

## Expected Edge
Crypto markets exhibit strong momentum during breakouts. Using ADX filters out choppy ranging markets, while ATR ensures stops are wide enough to survive crypto wicks.

## Data Requirements
- Columns needed: High, Low, Close
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Requires tuning of ATR multiplier for SuperTrend based on the coin's historical volatility.
---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/20260527_supertrend_pro]] · [[Trend_Momentum/20260526_supertrend_pro_volatility]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]] · [[Volatility_Breakout/20260527_avso_momentum]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]]
