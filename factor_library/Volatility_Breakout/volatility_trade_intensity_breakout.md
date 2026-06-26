## Strategy Name
Trade Intensity Volatility Breakout

## Category
Momentum

## Core Hypothesis — WHY should this strategy have an edge?
Volatility breakouts (e.g., Bollinger Band expansions) are often false signals if they occur on low participation. By using `num_trades` as a proxy for "Trade Intensity," we can filter for breakouts that are supported by a high frequency of individual transactions. A spike in trade count during a price breakout suggests that many participants (or many algorithmic executions) are reacting to the move, increasing the likelihood of a sustained short-term trend rather than a single large whale order creating a temporary price wick.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Price crosses above the **Upper Bollinger Band** (20, 2).
2. The current `num_trades` is > 2.0x the **Simple Moving Average** of `num_trades` over the last 20 periods ($Z_{intensity} > 2$).
3. Candle Close must be near the high (within top 25% of the candle range).

**Short Entry:**
1. Price crosses below the **Lower Bollinger Band** (20, 2).
2. The current `num_trades` is > 2.0x the **SMA** of `num_trades` (20).
3. Candle Close must be near the low.

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Price touches the opposite Bollinger Band.
- Or a fixed R:R of 1:2.

**Stop Loss:**
- Price closes back inside the Bollinger Band (Middle SMA-20).
- Time-stop: If no progress is made within 5 candles.

## Key Indicators / Data Required
- `num_trades` (Trade intensity/count).
- `close`, `high`, `low` (OHLC).
- Bollinger Bands (20, 2).
- SMA of `num_trades` (20).

## Timeframe Compatibility (scalp / swing / position)
Scalp / Day Trade (5m or 15m timeframes).

## Theoretical Risk — what market conditions break this strategy?
- **News Events:** High trade intensity during news can be extremely chaotic and lead to "whipsaws" where the price breaks out and immediately reverses.
- **Wash Trading:** Artificial inflation of trade counts by exchanges or bots can create fake "intensity" signals.
- **Late Entry:** Entering after the intensity has already peaked (exhaustion).

## Source — URL or reference
- "Trading Systems and Methods" by Perry Kaufman (Section on Transaction Frequency).
- Investopedia (Bollinger Band Breakout strategies).
- HFT research papers on "Trade Arrival Intensity" (Poisson processes in market microstructure).

## Interest Rating — [Medium-High]
Medium-High — Using transaction count adds a dimension of "crowd psychology" that price and volume alone sometimes miss.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/Bollinger_Bands]] · [[_Concepts/SMA]] · [[_Concepts/Trade_Intensity]]
