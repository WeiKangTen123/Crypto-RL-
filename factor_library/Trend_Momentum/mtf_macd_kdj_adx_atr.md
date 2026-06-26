---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: mtf-macd-kdj-adx-atr
source: Internal — multi-timeframe extension of macd_kdj_adx_atr
status: IMPLEMENTED
tags:
- implemented
timeframes: 1h
type: short-term
---
# Multi-Timeframe MACD KDJ ADX ATR Strategy

## Concept
Extends the MACD KDJ ADX ATR strategy by adding a 4H timeframe filter. Entry signals are generated on 1H bars but only allowed when the 4H trend and strength confirm the direction. 4H data is simulated via resampling from the 1H dataset.

## Entry Conditions
**Long (1H signal + 4H filter):**
- MACD histogram flip + KDJ golden cross + K oversold — on 1H
- ADX(1H) > 32.47
- Price above EMA(265) on 4H timeframe
- ADX(4H) > 17.35

**Short:**
- MACD + KDJ death cross + K overbought — on 1H
- ADX(1H) > 32.47
- Price below EMA(265) on 4H
- ADX(4H) > 17.35

## Exit Conditions
- ATR trailing stop: anchored to bar High (long) / Low (short), trails up as price moves
- ATR take profit: entry ± (3.15 × ATR)
- KDJ opposite cross on 1H

## Key Indicators
- MACD(4, 34, 17) on 1H — histogram flip
- KDJ(6) on 1H — cross at extreme zones (oversold: 28, overbought: 65)
- ADX(14) on both 1H and 4H
- EMA(265) on 4H — macro trend filter
- ATR(14) on 1H — trailing stop and TP sizing

## Expected Edge
Higher-timeframe confirmation dramatically reduces counter-trend noise. Entry window of 2 bars keeps signals tight. Trailing stop locks profit during extended trends.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1h (4H derived via resampling)
- Minimum history: 2 years

## Implementation Notes
- 4H indicators derived by resampling 1H OHLC data — no separate 4H dataset needed
- 4H values forward-filled to align with 1H index
- ATR SL trails upward (long) — not symmetric like a fixed SL

## Implementation Status: IMPLEMENTED

## Strategy Class
`MTF_MACDKDJ_ADX_ATR_Strategy` — `strategy_backtest/strategies/mtf_macd_kdj_adx_atr_strategy.py`

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
