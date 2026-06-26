## Strategy Name
Institutional Trade Intensity Breakout Filter

## Category
Volatility

## Core Hypothesis — WHY should this strategy have an edge?
Retail breakouts are often characterized by high price volatility but low actual trade participation. Institutional "Smart Money" moves are characterized by "Trade Intensity"—a high frequency of trades being executed in a short window. By using the `num_trades` column (available in Binance/CCXT spot data) as a filter, we can distinguish between a low-conviction "fakeout" and a high-conviction institutional trend start. High intensity indicates that algorithms are competing for fills, which usually leads to sustained momentum.

## Entry Signal — exact condition that triggers a buy
1. **Breakout:** Price closes above a 20-day high or the upper Bollinger Band (2.0 SD) on the 4h timeframe.
2. **Intensity Filter:** The `num_trades` for that 4h candle must be at least 2.5 standard deviations above its 24-period moving average.
3. **Spread Confirmation:** (If available) Bid-ask spread should remain tight during the spike, indicating deep liquidity providing the fills.

## Exit Signal — exact condition that triggers a sell or position close
1. **Trailing Stop:** Trail a 2-ATR stop loss from the highest close.
2. **Mean Reversion:** Exit if `num_trades` drops significantly while price remains flat (loss of institutional interest).
3. **Time Exit:** Close if no significant profit is made within 5-8 4h candles.

## Key Indicators / Data Required
- **Number of Trades (num_trades)**
- **4h OHLCV**
- **ATR (Average True Range)**

## Timeframe Compatibility (scalp / swing / position)
- **4h:** Ideal for capturing institutional trend shifts while filtering out intra-day noise.

## Theoretical Risk — what market conditions break this strategy?
"Flash Spikes" where a single large order triggers the intensity filter but doesn't have follow-through. Also, high-intensity "Chop" where many small orders cancel each other out in a ranging market.

## Source — URL or reference
- Concept aligned with HFT "Trade Intensity" research (e.g., VPIN - Volume-Synchronized Probability of Informed Trading).

## Interest Rating — [High]
High — Most technical indicators ignore the "count" of trades, only looking at volume. `num_trades` is a powerful hidden dimension of the dataset that DRL agents can use to identify high-participation regimes.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/Bollinger_Bands]] · [[_Concepts/Trade_Intensity]]
