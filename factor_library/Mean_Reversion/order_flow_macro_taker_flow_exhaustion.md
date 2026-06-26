## Strategy Name
Macro Taker-Flow Exhaustion

## Category
Order Flow

## Core Hypothesis — WHY should this strategy have an edge?
Institutional "climaxes" can be identified by extreme cumulative taker flow. On a 4h timeframe, when `taker_buy_base_vol` reaches a multi-day extreme relative to total volume, it often signifies exhaustion of the current trend (buying exhaustion or selling climax). Retail traders and momentum-chasing bots often pile in at the end of a move, creating a spike in taker volume that institutional players use as liquidity to exit their positions or flip bias. For a DRL agent, this provides a high-probability "reversal" signal to either close existing positions or initiate contrarian trades when the "dumb money" is most aggressive.

## Entry Signal — exact condition that triggers a buy
**Short Entry:**
1. Timeframe: 4h.
2. Price is at a 14-period (56-hour) High.
3. The ratio of `taker_buy_base_vol` to total `volume` is > 0.65 (65% of volume is taker buys), indicating potential buying exhaustion.
4. (Optional) Bearish divergence on RSI or a rejection wick from a key resistance level.

**Long Entry:**
1. Timeframe: 4h.
2. Price is at a 14-period Low.
3. The ratio of `taker_buy_base_vol` to total `volume` is < 0.35 (65% of volume is taker sells), indicating a selling climax.
4. (Optional) Bullish divergence on RSI or a long lower wick.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Mean reversion to the 20-period EMA.
- Or reaching the 50% retracement of the climax move.

**Stop Loss:**
- Price breaks and closes above/below the "climax" candle's extreme high/low.

## Key Indicators / Data Required
- `taker_buy_base_vol` (Taker buy volume).
- `volume` (Total volume).
- 20-period EMA.
- 14-period Donchian Channel or High/Low lookback.

## Timeframe Compatibility (scalp / swing / position)
Swing (4h timeframe).

## Theoretical Risk — what market conditions break this strategy?
- **Strong Trending Markets:** In a parabolic bull run, "exhaustion" signals can be followed by even more aggressive buying (short squeezes).
- **Exchange Bias:** Taker flow data can vary significantly between exchanges; relying on a single exchange's data might be misleading.
- **Large Liquidations:** Forced liquidations can spike taker volume without necessarily indicating a trend reversal, but rather a local liquidity event.

## Source — URL or reference
- "The Science of Algorithmic Trading and Portfolio Management" by Robert Kissell (Discussion on Taker/Maker imbalance).
- Journal of Financial Markets (Impact of Aggressive Orders on Price Discovery).

## Interest Rating — [High]
High — Taker/Maker imbalance is a direct measure of market "urgency," which is a powerful leading indicator for reversals when it reaches extremes.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/Donchian_Channel]] · [[_Concepts/EMA]] · [[_Concepts/Order_Flow]] · [[_Concepts/RSI]]
