## Strategy Name
Daily Range-Expansion with Intensity

## Category
Volatility

## Core Hypothesis — WHY should this strategy have an edge?
A price breakout on a daily (1d) timeframe can either be a "liquidity trap" (where price is pushed to trigger stops) or a "structural shift" (where institutional players are entering/exiting). By using `num_trades` (Trade Intensity) as a secondary filter, we can distinguish between these two. A "slow grind" up on low trade intensity is often fragile and prone to sharp reversals. Conversely, a breakout accompanied by a massive spike in transaction frequency suggests broad market participation and a higher probability of a sustained multi-day trend. For a DRL agent, this prevents "fading" a move that has significant institutional momentum.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Timeframe: 1d.
2. Daily Range (High - Low) is > 1.5x the 14-day **Average True Range (ATR)**.
3. Daily `num_trades` is > 1.5x the 20-day **Simple Moving Average** of `num_trades`.
4. Price closes above the previous day's high.
5. **Action:** Enter Long at the close of the breakout day.

**Short Entry:**
1. Timeframe: 1d.
2. Daily Range (High - Low) is > 1.5x the 14-day ATR.
3. Daily `num_trades` is > 1.5x the 20-day SMA of `num_trades`.
4. Price closes below the previous day's low.
5. **Action:** Enter Short at the close of the breakout day.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Price reaches 2.0x the ATR of the breakout day from the entry point.
- Or a trailing stop using the 20-day SMA.

**Stop Loss:**
- Price closes back inside the previous day's range.
- Or price breaks the low/high of the breakout candle.

## Key Indicators / Data Required
- `num_trades` (Daily transaction count).
- `ATR(14)` (Average True Range).
- `SMA(num_trades, 20)`.
- `high`, `low`, `close` (Daily OHLC).

## Timeframe Compatibility (scalp / swing / position)
Position (1d timeframe, held for days to weeks).

## Theoretical Risk — what market conditions break this strategy?
- **Exhaustion Gaps:** Sometimes a massive spike in intensity and range marks the *end* of a move (blow-off top) rather than the beginning.
- **Weekend Thin Liquidity:** High intensity on weekends might be less reliable due to lower overall participation from traditional institutions.
- **Bot Wars:** HFT bots can inflate `num_trades` without a clear directional bias, leading to false signals.

## Source — URL or reference
- "Technical Analysis of the Financial Markets" by John J. Murphy (Range expansion concepts).
- "Algorithmic and High-Frequency Trading" by Cartea, Jaimungal, and Penalva (Trade arrival intensity).

## Interest Rating — [High]
High — Combining structural price movement (Range) with execution frequency (Intensity) provides a robust filter for distinguishing trend shifts from noise.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/SMA]] · [[_Concepts/Trade_Intensity]]
