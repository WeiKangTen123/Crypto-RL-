## Strategy Name
Institutional ETF Flow Momentum

## Category
Macro / Cross-Asset (ETF flows, institutional liquidity)

## Core Hypothesis — WHY should this strategy have an edge?
Post-January 2024, Bitcoin's price discovery has transitioned to U.S.-regulated Spot ETFs (IBIT, FBTC, etc.). These vehicles represent institutional allocation, which tends to be "stickier" and trend-following rather than speculative. Significant net inflows create a "supply vacuum" on exchanges as ETF providers must purchase spot BTC to back their shares. This strategy exploits the delay between aggregated daily net inflow reports and the subsequent multi-day price pressure they create.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. **Indicator:** 5-day Moving Average (MA) of Net ETF Inflows (Aggregated across all US Spot ETFs).
2. **Condition:** The 5-day MA of net inflows must cross from negative to positive, OR show 3 consecutive days of increasing net inflows exceeding $200M/day.
3. **Confirmation:** Price must be above its own 20-day Simple Moving Average (SMA).

**Short / De-risk Signal (Hedge):**
1. **Condition:** The 5-day MA of net inflows turns negative for 2 consecutive days, OR a single day of "Extreme Outflow" exceeding -$500M.
2. **Action:** Close long positions or enter a delta-neutral hedge.

## Exit Signal — exact condition that triggers a sell or position close
1. **Take Profit:** When the 5-day MA of net inflows begins to decelerate (slope turns negative) while price is in a "premium" zone (e.g., above upper Bollinger Band).
2. **Stop Loss:** A 5% drawdown in price from the entry point, OR if aggregated net inflows turn negative for 3 consecutive days regardless of price.

## Key Indicators / Data Required
- **Aggregated ETF Net Inflows:** Daily data from sources like Farside Investors, Bloomberg, or Glassnode.
- **20-day SMA:** Simple Moving Average of BTC Price.
- **Price Data:** Daily OHLCV.

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** Swing / Position (Weekly holds).
- **Frequency:** Medium-term (Signals occur every 2-4 weeks).

## Theoretical Risk — what market conditions break this strategy?
1. **In-Kind Redemptions:** If institutions move BTC without selling (though spot ETFs are currently cash-create/redeem primarily), the flow signal may be decoupled from price.
2. **The "Grayscale overhang":** Massive outflows from high-fee products (like GBTC) can mask organic inflows into other products, creating noise in the aggregate signal.
3. **Macro Shocks:** Global "Black Swan" events will cause all assets to dump regardless of previous ETF inflow momentum.

## Source — URL or reference
Derived from 2024-2025 market observations by Bloomberg Intelligence (Eric Balchunas) and analysis of the "Institutional Supply Vacuum" theory.

## Interest Rating — [High] with one-line reason
High - This is the "God Candle" indicator for the 2024-2026 era; institutional flows are currently the single largest driver of BTC price discovery.

---
## Connections

**Category:** [[Cross_Sectional/_Index]]

**Indicators:** [[_Concepts/Bollinger_Bands]] · [[_Concepts/SMA]]
