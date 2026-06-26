## Strategy Name
Cross-L2 Liquidity Arbitrage

## Category
Cross-Exchange Arbitrage

## Core Hypothesis — WHY should this strategy have an edge?
As crypto liquidity fragments across various Layer 2s (Arbitrum, Base, Optimism, etc.) and AppChains, price discrepancies for the same assets frequently emerge and persist longer than they do on centralized exchanges. This strategy exploits these pricing inefficiencies by monitoring order book depth across major L2 DEXs. When the price deviation exceeds a threshold (accounting for bridge and swap fees), the agent executes a simultaneous buy/sell on the respective chains.

## Entry Signal — exact condition that triggers a buy
1. **Condition:** Price difference between DEX_A (e.g., Uniswap on Arbitrum) and DEX_B (e.g., Uniswap on Base) for a pair (e.g., WBTC/USDC) exceeds 0.5%.
2. **Constraint:** Order book depth on both DEXs is sufficient to cover the trade size without significant slippage.

## Exit Signal — exact condition that triggers a sell or position close
1. **Closing:** Position is closed automatically upon execution of the offsetting trade on the opposing DEX.
2. **Timeout:** If the arb opportunity does not close within 30 seconds, close both sides manually to minimize risk.

## Key Indicators / Data Required
- Real-time API access to DEX liquidity pools/order books across target L2s.
- Gas price monitors for both chains to calculate realistic cost-basis.

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** High-frequency scalp (milliseconds).

## Theoretical Risk — what market conditions break this strategy?
1. **Bridge/Chain Downtime:** A halt in bridging or chain congestion can leave one leg of the trade exposed.
2. **Gas Spikes:** Unforeseen gas increases can flip a profitable arb trade into a loss.
3. **Impermanent Loss:** If using AMM-based DEXs, slippage can quickly consume the arb margin.

## Source — URL or reference
Derived from 2026 microstructure research on fragmented L2 liquidity.

## Interest Rating — [High]
High — Highly profitable in high-volatility regimes where L2 bridges are congested.

---
## Connections

**Category:** [[Cross_Exchange_Arb/_Index]]

**Indicators:** [[_Concepts/Arbitrage]]
