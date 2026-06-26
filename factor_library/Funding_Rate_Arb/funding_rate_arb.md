# Strategy: Funding Rate Arbitrage (Market-Neutral Alpha)

## Overview
A market-neutral strategy that captures funding fees by taking simultaneous long (spot) and short (perpetual) positions.

## Alpha Source
Capturing the difference between spot price and perpetual contract price (funding fee).

## Expected ROI
8–15% APY.

## Risk Profile
Low. Primarily liquidation risk if the position is not hedged correctly or maintenance margin is breached.

## 2026 Context
Ideal for volatile markets where perpetual funding fees diverge significantly from the spot price.

## Implementation Steps (Pipeline)
1. Asset selection (BTC, ETH, SOL).
2. Connect to CEX API.
3. Calculate funding fee spread.
4. Execute hedge.
5. Monitor and rebalance.

---
## Connections

**Category:** [[Funding_Rate_Arb/_Index]]

**Indicators:** [[_Concepts/Funding_Rate]]
