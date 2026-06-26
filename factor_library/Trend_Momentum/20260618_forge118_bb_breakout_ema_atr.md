---
coins:
- ETH
interest: Medium
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- bollinger_band
- breakout
- ema_trend
- atr
- implemented
timeframes:
- 4h
type: volatility-breakout
---
# FORGE #118 — BB Breakout + EMA Trend Long + ATR TP/SL

## Concept
Bollinger Band breakout (close above upper band) filtered by a long-term EMA trend filter ensuring price is above a slow EMA, confirming macro uptrend before entering breakouts. Exits via ATR-based TP/SL.

## Entry Conditions
- Close breaks above Bollinger Band upper band

## Filter Conditions
- EMA trend long: close > long-period EMA (macro trend filter)

## Exit Conditions
- ATR TP/SL: take profit at sl_atr_mult × ATR below entry, TP at tp_atr_mult × ATR above entry

## Key Indicators
- Bollinger Bands (breakout signal)
- Slow EMA (macro trend filter)
- ATR (position sizing and exit)

## Expected Edge
BB breakout in the direction of the long-term trend has higher follow-through than counter-trend or sideways breaks. ATR exits dynamically adapt to volatility regime.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 3 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 118
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.18, ROI: 190%, MDD: 32%

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/20260618_forge121_bb_atr_clean]]
