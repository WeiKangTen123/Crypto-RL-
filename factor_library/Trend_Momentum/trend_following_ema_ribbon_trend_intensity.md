## Strategy Name
EMA Ribbon Trend-Intensity Filter

## Category
Trend Following

## Core Hypothesis — WHY should this strategy have an edge?
EMA ribbons (20, 50, 100, 200) are excellent for identifying established trends, but they often suffer from "lazy" signals where price drifts into the ribbon without momentum. By requiring a spike in `num_trades` (Trade Intensity), we filter for high-participation events. A spike in trade count typically represents institutional "order splitting" or high-frequency bot activity, signaling that the trend has sufficient fuel to continue rather than stalling or reversing.

## Entry Signal — exact condition that triggers a buy
1. **Ribbon Alignment:** The 20 EMA > 50 EMA > 100 EMA > 200 EMA (Bullish stack).
2. **Price Action:** Price touches or enters the zone between the 20 and 50 EMA.
3. **Intensity Filter:** `num_trades` for the current candle must be at least 1.5x the rolling 20-period average of `num_trades`.
4. **Trigger:** Close above the 20 EMA following the intensity spike.

## Exit Signal — exact condition that triggers a sell or position close
1. **Trend Breakdown:** Price closes below the 100 EMA.
2. **Momentum Loss:** Exit if the 20 EMA crosses below the 50 EMA.
3. **Take Profit:** Dynamic ATR-based trailing stop (2.5x ATR).

## Key Indicators / Data Required
- OHLCV Data
- `num_trades` (Trade Intensity)
- EMA Ribbon (20, 50, 100, 200)
- ATR (for exit management)

## Timeframe Compatibility (scalp / swing / position)
- **Swing:** 1H and 4H timeframes. The 4H provides the macro trend, while the 1H offers the intensity-confirmed entry.

## Theoretical Risk — what market conditions break this strategy?
- **Low-Volatility "Grind":** If the market moves higher with consistently low trade intensity, the strategy will stay out, missing the move.
- **Blow-off Tops:** Extremely high `num_trades` can sometimes signal exhaustion rather than continuation if price is already extended far from the 200 EMA.

## Source — URL or reference
Internal Research - EMA Ribbon + Trade Intensity Alpha

## Interest Rating — [High] with one-line reason
High - Combines classic trend-following with "participation conviction" metrics unique to crypto exchange data.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/Trade_Intensity]]
