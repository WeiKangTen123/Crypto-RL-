## Strategy Name
Cumulative Volume Delta (CVD) Absorption Divergence

## Category
Order Flow

## Core Hypothesis — WHY should this strategy have an edge?
Standard price charts only show the result of auctions, not the intent of the participants. HFTs look at the imbalance between aggressive (market) orders and passive (limit) orders. On a 1h timeframe, if price makes a lower low but the Cumulative Volume Delta (CVD) makes a higher low, it reveals a "selling climax" where aggressive sellers are being absorbed by passive institutional limit buyers. This exhaustion of aggressive supply often leads to a sharp upward reversal as the market becomes "thin" on the bid side and price snaps back to find liquidity.

## Entry Signal — exact condition that triggers a buy
1. **Price Condition:** Price makes a lower low compared to the previous 24-48 hours.
2. **CVD Condition:** 1h CVD (Taker Buy Vol - Taker Sell Vol) makes a higher low over the same period.
3. **Volume Trigger:** A 1h candle closes with a "hammer" or "doji" shape, confirmed by a spike in total volume.

## Exit Signal — exact condition that triggers a sell or position close
1. **Target:** 2:1 Reward-to-Risk ratio or a touch of the 20-period EMA on the 4h chart.
2. **Invalidation:** Price closes significantly below the signal low.
3. **Exhaustion:** Exit if CVD shows a bearish divergence (price higher high, CVD lower high) at local resistance.

## Key Indicators / Data Required
- **Taker Buy Base Volume** (Aggressor Buy)
- **Taker Sell Base Volume** (Aggressor Sell)
- **CVD = Cumulative(Taker Buy - Taker Sell)**
- **1h OHLCV**

## Timeframe Compatibility (scalp / swing / position)
- **1h:** Primary timeframe for signal identification.
- **4h:** Used for secondary trend confirmation.

## Theoretical Risk — what market conditions break this strategy?
This strategy fails in "Waterfall" sell-offs or massive liquidation events where the aggressive selling pressure is so high that limit orders are simply steamrolled. Passive absorption only works when the aggressive flow is exhausted.

## Source — URL or reference
- Derived from standard "ExoCharts" and "VeloData" order flow principles.
- Quantitative research on "Kyle's Lambda" and market microstructure absorption.

## Interest Rating — [High]
High — Order flow data is a "leading" indicator compared to lagging indicators like RSI or MACD. For a DRL agent, having the raw delta values provides a direct view of market participant aggression.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/MACD]] · [[_Concepts/Order_Flow]] · [[_Concepts/RSI]]
