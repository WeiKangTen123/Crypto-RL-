---
coins:
- ETH
interest: Medium
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- rsi
- atr_expansion
- ema_trend
- stability
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #119 — RSI Trend + ATR Expansion + EMA Trend Short

## Concept
RSI trend-following signal (RSI above midline and trending up) combined with ATR expansion filter (volatility expanding) and short-term EMA trend confirmation. The combination of three confirmations significantly reduces false signals.

## Entry Conditions
- RSI trending up above midline (rsi_trend signal)

## Filter Conditions
- ATR expansion: current ATR > ATR moving average (volatility expanding)
- EMA trend short: close > short-period EMA

## Exit Conditions
- ATR TP/SL

## Key Indicators
- RSI (14-period trend signal)
- ATR expansion ratio
- Short EMA trend filter

## Expected Edge
Three-layer confirmation (momentum + volatility expansion + trend) ensures entries occur only during high-conviction trending conditions, dramatically reducing churn trades.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 119
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.04, MDD: 23% (lowest MDD of V2 batch)

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/RSI]] · [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/20260618_forge127_ema_wr_short_tight]]
