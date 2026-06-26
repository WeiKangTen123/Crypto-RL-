## Strategy Name
Liquidation Cascade Front-running

## Category
Order Flow

## Core Hypothesis — WHY should this strategy have an edge?
BTC price gravitates toward high-liquidity zones where large clusters of leveraged positions are likely to be forcibly liquidated. Market makers and whales often push the price toward these clusters to "harvest" liquidity. When a cluster is hit, it triggers a chain reaction (cascade/squeeze) as forced orders hit the market. Front-running the entry into these zones or trading the reversal after the "sweep" exploits the predictable, non-discretionary nature of liquidation orders.

## Entry Signal — exact condition that triggers a buy
**Long Entry (Short Squeeze Front-run):**
1. Identify a high-intensity "Short Liquidation" cluster on a Liquidation Map/Heatmap (e.g., bright yellow zone).
2. Monitor Cumulative Volume Delta (CVD) and Open Interest (OI).
3. Trigger long when price approaches within 0.2% of the cluster and OI starts to spike (indicating aggressive fresh longing) or CVD shows a bullish divergence.

**Long Entry (Long Liquidation Reversal/Sweep):**
1. Price "sweeps" through a major Long Liquidation cluster.
2. The liquidation cluster on the map "disappears" (positions cleared).
3. Trigger long on the first 1-minute candle that closes back above the bottom of the liquidation zone.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Target the "end" of the liquidation cluster (where the map shows low density/purple).
- Trailing stop-loss once price enters the "squeeze" phase.

**Stop Loss:**
- If price stalls inside the cluster and OI begins to drop sharply without further price progress.
- Fixed stop-loss placed in a "low-liquidity" (purple) zone on the map.

## Key Indicators / Data Required
- Liquidation Map (Heatmap) data (e.g., from CoinGlass or KingFisher).
- Aggregate Open Interest (OI).
- Cumulative Volume Delta (CVD).
- Real-time Liquidation feeds (WebSocket).

## Timeframe Compatibility (scalp / swing / position)
Scalp / Day Trade (minutes to hours).

## Theoretical Risk — what market conditions break this strategy?
- **Low Volatility:** In ranging markets, price may never reach the clusters, or the "magnetic" pull may be weak.
- **Data Accuracy:** Liquidation maps are model-based predictions, not actual exchange data; models can be wrong about where leverage is concentrated.
- **Exhaustion:** If the market is too thin, a cascade may be smaller than expected.

## Source — URL or reference
- CoinGlass (Liquidation Heatmaps)
- KingFisher / Velo Data tutorials
- Mudrex blog on Liquidation Map trading

## Interest Rating — [High]
High — Liquidation events are the single most significant drivers of "violent" price action in BTC, making them ideal for DRL agents to learn for both alpha generation and risk avoidance.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/Order_Flow]]
