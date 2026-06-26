---
coins:
- BTC
- ETH
interest: High
name: EMA Crossover
source: TradingView
status: QUEUED
tags:
- queued
timeframes:
- 1h
- 4h
type: long-term
---
# EMA Crossover

## Concept
A simple trend-following strategy that uses two Exponential Moving Averages (EMAs) to identify trend direction. A "Golden Cross" (fast EMA crosses above slow EMA) signals a potential uptrend and a long entry. A "Death Cross" (fast EMA crosses below slow EMA) signals a potential downtrend and an exit.

## Entry Conditions
- Fast EMA crosses above Slow EMA.

## Exit Conditions
- Fast EMA crosses below Slow EMA.

## Key Indicators
- Fast EMA (e.g., 9-period)
- Slow EMA (e.g., 21-period)

## Expected Edge
This strategy aims to capture profits from sustained trends in the crypto market. By using EMAs, it filters out short-term noise and focuses on the underlying trend.

## Data Requirements
- Columns needed: Close
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- The periods for the fast and slow EMAs are configurable and should be optimized.
- This strategy is prone to whipsaws in ranging markets.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/20260526_rsi_trend_filter]]
