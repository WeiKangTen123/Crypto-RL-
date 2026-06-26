## Strategy Name
Fair Value Gap (FVG) Recovery

## Category
Market Structure

## Core Hypothesis — WHY should this strategy have an edge?
Fair Value Gaps (FVGs) represent areas of price inefficiency where a rapid, impulsive move occurred, leaving many orders unfilled. Market participants (especially institutional players or algorithms) often seek to re-test or "fill" these gaps to achieve a more efficient price discovery. These zones act as magnets for price re-balancing. Trading the recovery (retrace) into these gaps exploits the tendency of markets to return to equilibrium before continuing a trend.

## Entry Signal — exact condition that triggers a buy
**Long Entry (Bullish Recovery):**
1. Identify a Bullish FVG (Gap between the High of Candle 1 and the Low of Candle 3 in a 3-candle sequence).
2. Wait for price to retrace downward into the gap.
3. **Entry Trigger:** Buy when price hits the **Consequent Encroachment (CE)**—the 50% midpoint of the FVG.
4. **Alternative Trigger:** Buy on a 5m/15m bullish engulfing candle formed inside the 1H/4H FVG.

**Short Entry (Bearish Recovery):**
1. Identify a Bearish FVG (Gap between the Low of Candle 1 and the High of Candle 3).
2. Wait for price to rally upward into the gap.
3. **Entry Trigger:** Sell at the 50% midpoint (CE) of the FVG or on a bearish reversal pattern within the gap.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- TP1: The "Swing High" or "Swing Low" that was created by the original impulsive move.
- TP2: The next major FVG or Liquidity Pool (e.g., Previous Day's High/Low).

**Stop Loss:**
- Standard: Place stop-loss just beyond the origin of the gap (the wick of Candle 1).
- Invalidation: If price closes a full candle body through the FVG (Inverted FVG).

## Key Indicators / Data Required
- Multi-timeframe Price Action (OHLCV).
- FVG detection logic (identifying non-overlapping 3-candle wicks).
- Volume (to confirm low-volume retrace and high-volume bounce).

## Timeframe Compatibility (scalp / swing / position)
Scalp / Day Trade (typically using 15m or 1H for identification and 1m/5m for execution).

## Theoretical Risk — what market conditions break this strategy?
- **Strong Trend Change:** If the market is undergoing a fundamental shift, it may ignore old gaps and create new ones (Breakaway Gaps).
- **Inverted FVGs:** Gaps that are "sliced through" become resistance/support for the opposite direction, potentially trapping traders.
- **Whipsaws:** High volatility events can cause price to wick far beyond the FVG before returning, hitting stop-losses.

## Source — URL or reference
- Mudrex: Fair Value Gap Trading Strategy
- Alchemy Markets: How to trade FVGs
- ICT (Inner Circle Trader) concepts

## Interest Rating — [Medium]
Medium — While highly popular and effective in trending markets, it requires multi-timeframe context and can be prone to "false fills" in choppy, low-liquidity environments.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/FVG]]
