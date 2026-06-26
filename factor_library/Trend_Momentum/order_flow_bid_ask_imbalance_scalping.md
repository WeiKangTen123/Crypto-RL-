## Strategy Name
Bid-Ask Imbalance Scalping

## Category
Order Flow

## Core Hypothesis — WHY should this strategy have an edge?
Prices in high-frequency environments tend to move toward the "thinner" side of the order book (the side with less volume). A significant imbalance suggests that one side (e.g., buyers) is overwhelming the other (e.g., sellers), or that the "thick" side acts as a temporary price floor/ceiling that is harder to penetrate than the "thin" side. This exploits short-term liquidity exhaustion and the reactive behavior of market participants and market-making algorithms.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Calculate Imbalance ($\rho$) using the top $L$ levels (typically 5-10): $\rho = (V_{bid} - V_{ask}) / (V_{bid} + V_{ask})$.
2. Trigger long when $\rho > 0.6$ (threshold adjustable based on volatility).
3. Confirm with **Weighted Mid-Price** leaning significantly higher than the standard Mid-Price.

**Short Entry:**
1. Trigger short when $\rho < -0.6$.
2. Confirm with Weighted Mid-Price leaning significantly lower than standard Mid-Price.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Exit when the Imbalance ($\rho$) returns to a neutral zone (between -0.1 and 0.1) or flips sign.
- Fixed micro-target (e.g., 0.05% - 0.1% for HFT scalping).

**Stop Loss:**
- Exit if $\rho$ rapidly flips to the opposite extreme (e.g., from > 0.6 to < -0.4).
- Time-based exit: If the predicted price move does not occur within 10-30 seconds (edge decay).

## Key Indicators / Data Required
- Real-time Level 2 Order Book (L2 snapshots or WebSockets).
- $V_{bid}$ and $V_{ask}$ (cumulative volume at top $L$ levels).
- Weighted Mid-Price: $(Bid \cdot V_{ask} + Ask \cdot V_{bid}) / (V_{bid} + V_{ask})$.
- Imbalance Ratio ($\rho$).

## Timeframe Compatibility (scalp / swing / position)
Scalp (HFT-adjacent, sub-minute hold times).

## Theoretical Risk — what market conditions break this strategy?
- **Spoofing/Layering:** Large players placing and quickly cancelling fake orders to manipulate the imbalance ratio.
- **Latency:** High-latency execution will miss the narrow window of opportunity (seconds).
- **High Fees:** The expected gain per trade is often smaller than the taker fee on many exchanges, requiring high-volume/VIP fee tiers.

## Source — URL or reference
- Towards Data Science (Stoikov's research on Order Book Imbalance)
- Bitsgap (Order Book Imbalance metrics)

## Interest Rating — [High]
High — This provides a direct look at the "engine room" of price discovery and is a foundational feature for DRL agents learning short-term price dynamics.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/Order_Flow]]
