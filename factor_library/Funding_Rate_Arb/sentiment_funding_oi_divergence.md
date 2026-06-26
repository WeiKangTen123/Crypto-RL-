## Strategy Name
Sentiment & Order Flow Divergence (Funding/OI Hunt)

## Category
Sentiment (Fear & Greed Index, funding rate, open interest)

## Core Hypothesis — WHY should this strategy have an edge?
Crypto markets are unique due to the dominance of perpetual futures and high leverage. When price trends strongly, speculative traders often "pile in," driving Open Interest (OI) and Funding Rates to extreme levels. This creates an unstable equilibrium where even a minor price stall or reversal can trigger a "cascading liquidation" event (Long or Short Squeeze). This strategy identifies these "fragile" market states by looking for divergences between price and OI, and extremes in funding rates, allowing us to bet on high-velocity reversals.

## Entry Signal — exact condition that triggers a buy
**Bullish Reversal (Short Squeeze):**
1. **Indicator:** Open Interest (OI) and Funding Rate on 1-hour timeframe.
2. **Condition 1:** Price is making a "Lower Low" while OI is making a "Higher High" (New shorts entering aggressively at the bottom).
3. **Condition 2:** Funding Rate is **negative** (Shorts are paying longs).
4. **Trigger:** A bullish reversal candle (wick) on the 15m timeframe accompanied by a sudden **drop** in OI (shorts starting to cover).

**Bearish Reversal (Long Squeeze):**
1. **Condition 1:** Price is making a "Higher High" while OI is making a "Higher High" (Extreme fomo).
2. **Condition 2:** Funding Rate is **highly positive** (>0.03% per 8h).
3. **Trigger:** A bearish rejection candle on the 15m timeframe accompanied by a drop in OI.

## Exit Signal — exact condition that triggers a sell or position close
1. **Primary Target:** The "equilibrium" level (where the liquidation spike started).
2. **Momentum Exit:** Exit when the OI stabilizes and stops falling (liquidation cascade has ended).
3. **Stop Loss:** Placed just above/below the rejection wick (0.3% - 0.5% risk).
4. **Time Exit:** Close after 4-8 hours if the cascade doesn't materialize.

## Key Indicators / Data Required
- **Open Interest (OI):** Aggregated across major exchanges (Binance, Bybit).
- **Funding Rate:** Perpetual contract funding fees.
- **Price Data:** 15m and 1h OHLCV.

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** Intraday (15m execution / 1h context).
- **Strategy Type:** Mean Reversion / Contrarian.

## Theoretical Risk — what market conditions break this strategy?
1. **Institutional Spot Buying:** If a price pump is driven by Spot ETFs rather than futures, funding will remain neutral/low and OI may stay flat. In this case, "shorting the top" will result in a loss as there is no leverage to squeeze.
2. **Infinite Trending:** During extreme bull/bear runs, funding can stay "too high" or "too low" for weeks as new capital keeps flowing in.
3. **Exchange Downtime:** High-volatility liquidation events often crash exchange APIs, making execution difficult.

## Source — URL or reference
Standard crypto "Order Flow" trading methodology used by professional perpetual traders and delta-neutral funds.

## Interest Rating — [High] with one-line reason
High - This is the "secret sauce" of crypto trading; it allows the agent to distinguish between a healthy trend and a fragile, leverage-fueled bubble.

---
## Connections

**Category:** [[Funding_Rate_Arb/_Index]]

**Indicators:** [[_Concepts/Funding_Rate]] · [[_Concepts/Order_Flow]]
