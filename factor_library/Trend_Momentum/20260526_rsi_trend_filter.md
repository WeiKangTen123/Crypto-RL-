---
coins:
- BTC
- ETH
interest: High
name: RSI Trend Filter
source: TradingView
status: QUEUED
tags:
- queued
timeframes:
- 1h
- 4h
type: long-term
---
# RSI with 200 EMA Trend Filter

## Concept
A trend-following strategy that uses a long-term EMA to filter for uptrends and the Relative Strength Index (RSI) to identify entry points. It aims to "buy the dip" in an established bull market.

## Entry Conditions
- Price is above the 200-period EMA.
- RSI crosses above the oversold threshold (e.g., 30).

## Exit Conditions
- A fixed take profit or stop loss, or when the trend filter is violated (price crosses below 200 EMA).

## Key Indicators
- 200-period EMA
- RSI (e.g., 14-period)

## Expected Edge
This strategy attempts to improve on simple trend-following by timing entries during pullbacks, potentially leading to better risk-reward ratios. The 200 EMA acts as a regime filter.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- The RSI period and oversold/overbought levels are configurable and should be optimized.
- The take profit and stop loss levels are also critical parameters to optimize.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Trend_Momentum/20260526_ema_crossover]]
