## Strategy Name
Dual-EMA Crossover with Volatility Expansion

## Category
Trend Following

## Core Hypothesis — WHY should this strategy have an edge?
EMA crossovers (9 and 21) are effective in trending markets but generate many "fakeouts" during consolidations. In crypto, a genuine trend shift is almost always accompanied by a surge in trade count (`num_trades`) as new participants enter the market. By filtering for "volatility expansion" via trade intensity at the moment of the crossover, we significantly increase the probability that the crossover represents a "structural break" rather than a temporary oscillation.

## Entry Signal — exact condition that triggers a buy
1. **Crossover:** 9 EMA crosses above the 21 EMA on the Daily (1D) timeframe.
2. **Volatility Confirmation:** `num_trades` for the crossover candle (or the 3 candles leading up to it) must be at least 2 standard deviations above the 50-day mean of `num_trades`.
3. **Volume Check:** Total Volume must also be increasing relative to the previous 5 days.
4. **Trigger:** Daily candle close after the crossover + intensity spike.

## Exit Signal — exact condition that triggers a sell or position close
1. **Trend Reversal:** 9 EMA crosses back below the 21 EMA.
2. **Trailing Stop:** Exit if price closes below the 50-day Simple Moving Average (SMA).
3. **Parabolic Exit:** If daily RSI exceeds 85, tighten stop loss to the previous day's low.

## Key Indicators / Data Required
- Daily OHLCV Data
- `num_trades` (Trade Intensity)
- 9 EMA, 21 EMA
- 50 SMA (Macro support)

## Timeframe Compatibility (scalp / swing / position)
- **Swing / Position:** Daily (1D) chart. Designed for capturing multi-week or multi-month BTC moves.

## Theoretical Risk — what market conditions break this strategy?
- **Exhaustion Gaps:** Occasionally, a massive spike in trade intensity marks the *end* of a move rather than the beginning (climax volume).
- **Exchange Maintenance/Outages:** Data gaps in `num_trades` can lead to missed or false signals if not normalized.

## Source — URL or reference
Internal Research - EMA Crossover Optimization via Intensity Filters

## Interest Rating — [High] with one-line reason
High - Simple, robust macro logic that leverages trade count to filter out the noise typical of Bitcoin's range-bound phases.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/RSI]] · [[_Concepts/SMA]] · [[_Concepts/Trade_Intensity]]
