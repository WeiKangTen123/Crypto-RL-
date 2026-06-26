## Strategy Name
Taker-Flow Momentum Scalping

## Category
Order Flow

## Core Hypothesis — WHY should this strategy have an edge?
Market movements are driven by the aggression of participants. "Taker" volume represents traders who are willing to pay the spread to execute immediately, signaling urgency. When `taker_buy_base_vol` significantly exceeds the remaining volume (taker sell volume) in a short window (1m), it indicates a localized supply/demand imbalance. This aggressive "buying into the ask" often creates a momentum tail that can be scalped for small, high-probability gains before the liquidity resets.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. Timeframe: 1-minute (1m).
2. Calculate the **Taker Buy Ratio**: $R = \text{taker\_buy\_base\_vol} / \text{volume}$.
3. Trigger long when $R > 0.65$ and the candle is bullish (Close > Open).
4. (Optional) Filter: Ensure `volume` is above its 20-period moving average to avoid low-liquidity noise.

**Short Entry:**
1. Calculate the **Taker Sell Volume**: $\text{taker\_sell} = \text{volume} - \text{taker\_buy\_base\_vol}$.
2. Calculate the **Taker Sell Ratio**: $R_{sell} = \text{taker\_sell} / \text{volume}$.
3. Trigger short when $R_{sell} > 0.65$ and the candle is bearish (Close < Open).

## Exit Signal — exact condition that triggers a sell or position close
**Profit Take:**
- Fixed target of 0.15% - 0.30% (appropriate for 1m BTC scalping).
- Exit immediately if the Taker Ratio $R$ drops below 0.50 in the subsequent candle.

**Stop Loss:**
- Exit if the price closes below the entry candle's low (for longs) or above the entry candle's high (for shorts).
- Hard stop at 0.15%.

## Key Indicators / Data Required
- `taker_buy_base_vol` (Aggressor buy volume).
- `volume` (Total volume).
- `close`, `open`, `low`, `high` (1m OHLC).

## Timeframe Compatibility (scalp / swing / position)
Scalp (1m or 5m timeframes; holding time usually 1-5 minutes).

## Theoretical Risk — what market conditions break this strategy?
- **Mean Reversion / Range-bound markets:** In low-volatility ranges, aggressive takers might just be "filling the range" rather than starting a trend.
- **Iceberg Orders:** Large limit orders (hidden) can absorb all taker volume without price moving, leading to a "momentum trap."
- **High Fees:** Frequent scalping requires low fee tiers to remain profitable after slippage.

## Source — URL or reference
- Binance Academy (Taker vs Maker volume concepts)
- QuantConnect (Directional Volume Intensity research)
- VPIN (Volume-Synchronized Probability of Informed Trading) logic by Easley et al.

## Interest Rating — [High]
High — This is one of the most "pure" indicators of market intent available in standard OHLCV+ datasets without needing full L2 books.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/Order_Flow]]
