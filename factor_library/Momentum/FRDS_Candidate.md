---
coins:
- BTC
- ETH
- BNB
- SOL
- XRP
status: IMPLEMENTED
tags:
- implemented
timeframes:
- 4h
---
# Funding Rate Divergence Squeeze (FRDS)

## Alpha Premise
When price is trending downwards but the funding rate is trending upwards (getting more positive), it indicates persistent "dip buying" by leveraged longs. This divergence creates a coiled spring for a Long Squeeze. The reverse is true for Short Squeezes.

## Math & Logic
- **`Price_Trend`** = Linear regression slope of close price over 12 periods (2 days).
- **`FR_Trend`** = Linear regression slope of Funding Rate over 12 periods.
- **`Spot_OBI`** = (Bid_Depth - Ask_Depth) / (Bid_Depth + Ask_Depth).
- **Entry Short (Long Squeeze)**: `Price_Trend` < 0 AND `FR_Trend` > 0 AND `Spot_OBI` < 0.
- **Entry Long (Short Squeeze)**: `Price_Trend` > 0 AND `FR_Trend` < 0 AND `Spot_OBI` > 0.
- **Holding Period**: MFT (multi-day squeeze continuation).

## Strategy Play Style
Trend continuation via leveraged flush-outs. High probability momentum setups.

## Strategic Disadvantages
Relies on perpetual futures being the primary driver of market structure.

## Enhancement Recommendations
1. Scale position size based on the magnitude of the `FR_Trend`.
2. Exit criteria should include a sharp reversion of the Funding Rate back to the mean.

## Agent Reasoning (Chain of Thought)
Divergences between price and derivatives positioning are powerful. Instead of catching falling knives, we trade in the direction of the underlying spot trend, waiting for the counter-trend leveraged traders to exhaust themselves and get squeezed.
