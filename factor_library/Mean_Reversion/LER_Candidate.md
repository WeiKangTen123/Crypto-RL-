---
coins:
- BTC
- ETH
- SOL
status: IMPLEMENTED
tags:
- implemented
timeframes:
- 4h
- 1h
---
# Liquidity Exhaustion Reversal (LER)

## Alpha Premise
Whales sweep retail liquidity. A "liquidity sweep" happens when the price moves sharply into a zone, wiping out top-level order book depth, followed by an immediate reversal. We detect this by looking for price extremes accompanied by sudden imbalances in the Ask-Bid depth.

## Math & Logic
- **`Depth_Imbalance`** = Ask_Depth - Bid_Depth.
- **Entry Short**: Price touches Upper Bollinger Band (20, 2) AND `Depth_Imbalance` > 90th percentile of last 100 periods (asks pile up, bids pulled, liquidity exhausted).
- **Entry Long**: Price touches Lower Bollinger Band (20, 2) AND `Depth_Imbalance` < 10th percentile of last 100 periods (bids pile up, asks pulled).
- **Holding Period**: MFT (~1-3 days).

## Strategy Play Style
Mean Reversion at structural liquidity sweeps. Best in ranging markets or low-to-medium volatility chop.

## Strategic Disadvantages
Will get trapped if the extreme depth imbalance is actually institutional accumulation/distribution rather than exhaustion.

## Enhancement Recommendations
1. Validate the sweep with Cumulative Volume Delta (CVD).
2. Use dynamic take-profits based on return to the 20-period VWAP.

## Agent Reasoning (Chain of Thought)
Order book depth on its own is noisy, but when combined with a statistical price extreme (Bollinger Bands), a sudden collapse in supporting depth signals that the move is a stop-run and lacks the liquidity to continue.
