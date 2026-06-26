---
coins: [BTC, ETH, BNB, SOL, XRP]
timeframes: [4h, 1h]
status: IMPLEMENTED
---
# Extreme Funding Rate Mean Reversion with Spot OBI (EFR-MR)

## Alpha Premise
Funding rates tend to mean-revert. When funding is extremely positive (retail overly long on perps), the perp price > spot price. However, naive mean reversion fails during strong trends. By gating the entry with Spot Order Book Imbalance (OBI), we ensure that the spot market is providing the counter-pressure (selling) needed to force a reversion.

## Math & Logic
- **`FR_Z_Score`** = Z-score of Funding Rate over 84 periods (14 days on 4H).
- **`Spot_OBI`** = (Bid_Depth - Ask_Depth) / (Bid_Depth + Ask_Depth) using top 1% depth.
- **Entry Short**: `FR_Z_Score` > 2.0 AND `Spot_OBI` < -0.3.
- **Entry Long**: `FR_Z_Score` < -2.0 AND `Spot_OBI` > 0.3.
- **Holding Period**: MFT (~2-3 days).

## Strategy Play Style
Counter-trend funding basis capture. Excellent in high-leverage late-trend environments where retail is aggressively chasing moves but spot whales are capping the price.

## Strategic Disadvantages
Vulnerable during violent price discovery phases (all-time-high breakouts) where funding can stay maximally positive for weeks.

## Enhancement Recommendations
1. Add a Volume-Weighted gating mechanism to ensure the spot sell wall is actually being hit by volume.
2. Filter trades based on overall market regime.

## Agent Reasoning (Chain of Thought)
Traditional mean reversion of funding rates often gets run over by momentum. By pairing perp funding extremes with spot order book imbalance, we align with the "smart money" (spot limit orders) fading the "dumb money" (perp market orders).
