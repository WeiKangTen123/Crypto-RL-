## Strategy Name
Intraday Liquidation Sweep (Liquidity Hunt)

## Category
Market Structure (support/resistance, fair value gaps, liquidity sweeps)

## Core Hypothesis — WHY should this strategy have an edge?
Large institutional players ("whales") require significant liquidity to enter or exit large positions without causing excessive slippage. They often find this liquidity at "pools" where retail traders place stop-loss orders (e.g., just above previous session highs or below previous day lows). By driving price into these pools, they trigger a cascade of market orders (liquidations), which provides the depth needed to fill their own counter-trend orders. This strategy exploits the subsequent "mean reversion" after the weak hands have been flushed out.

## Entry Signal — exact condition that triggers a buy
**Bullish Setup (Long):**
1. **Identify Liquidity Pool:** Mark the Previous Day Low (PDL) or the session low (Asia/London/NY).
2. **The Sweep:** Price must aggressively drop below the marked level but fail to close significantly below it on the 1H timeframe (look for a long lower wick).
3. **Structure Shift (M5/M15):** On a lower timeframe (5m or 15m), wait for price to break the most recent "Lower High" (Market Structure Shift).
4. **Displacement Entry:** Look for a Fair Value Gap (FVG) or a Bullish Order Block created by the impulsive move back into the range. Enter on a retest of this FVG/OB.

**Bearish Setup (Short):**
1. **Identify Liquidity Pool:** Mark the Previous Day High (PDH) or the session high.
2. **The Sweep:** Price spikes above the marked level but produces a quick rejection (upper wick).
3. **Structure Shift (M5/M15):** On a lower timeframe, wait for price to break the most recent "Higher Low".
4. **Displacement Entry:** Enter on a retest of the Bearish FVG or Order Block created by the rejection move.

## Exit Signal — exact condition that triggers a sell or position close
1. **Target 1 (Partial):** The 50% retracement (equilibrium) of the range.
2. **Target 2 (Final):** The opposite liquidity pool (e.g., if you swept the low, target the high).
3. **Stop Loss:** Placed strictly below/above the "Sweep Wick" (the absolute low/high of the rejection). If price breaches this level again, the sweep thesis is invalidated.
4. **Risk Management:** Aim for a minimum Risk-to-Reward ratio of 1:2.5.

## Key Indicators / Data Required
- **Price Action:** OHLCV data.
- **Session Indicators:** To automatically mark London/NY/Asia highs and lows.
- **Market Structure mapping:** Identification of swing highs/lows and structure shifts.
- **Optional Confluence:** High Volume on the sweep wick and subsequent "displacement" volume.

## Timeframe Compatibility (scalp / swing / position)
- **Context:** 1H or 4H for identifying the major liquidity pools.
- **Execution:** 1m, 5m, or 15m for the structure shift and entry (Scalp/Intraday).

## Theoretical Risk — what market conditions break this strategy?
1. **Strong Trending Markets:** In a "parabolic" trend, price may sweep a high and simply keep going (continuation) instead of reversing. This is why the Market Structure Shift (MSS) on a lower timeframe is a mandatory filter.
2. **News Events:** High-impact news can create multiple sweeps in both directions (choppiness), leading to stop-outs before the real move happens.
3. **Low Liquidity periods:** Sweeps during low-volume weekends may lack the institutional follow-through required for a reversal.

## Source — URL or reference
Core concept derived from ICT (Inner Circle Trader) and SMC (Smart Money Concepts) methodologies, adapted for BTC's 24/7 high-volatility environment.

## Interest Rating — [High] with one-line reason
High - This strategy is highly active and directly targets the "stop-loss" behavior of retail traders, which is a prime feature for a DRL agent to learn.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/FVG]]
