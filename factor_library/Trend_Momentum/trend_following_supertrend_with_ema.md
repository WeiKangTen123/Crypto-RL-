## Strategy Name
Supertrend with EMA Filter

## Category
Trend Following

## Core Hypothesis — WHY should this strategy have an edge?
Bitcoin exhibits strong, sustained trends but is prone to high-volatility noise. This strategy uses the 200-period Exponential Moving Average (EMA) as a "macro filter" to ensure trades are aligned with the primary trend, while the Supertrend indicator (based on Average True Range) provides a volatility-adjusted entry trigger that accounts for BTC's specific price action characteristics.

## Entry Signal — exact condition that triggers a buy
1. **Trend Filter:** Price must be trading above the 200 EMA.
2. **Momentum Trigger:** The Supertrend indicator (10, 3) must flip from Red (Bearish) to Green (Bullish).
3. **Confirmation:** The current candle must close above the Green Supertrend line.

## Exit Signal — exact condition that triggers a sell or position close
1. **Trend Reversal:** Exit when the Supertrend flips from Green to Red.
2. **Trailing Stop:** Position is closed if the price closes below the current Green Supertrend line.
3. **Optional:** Fixed Risk/Reward target of 1:2.

## Key Indicators / Data Required
- OHLCV Data (Price/Volume)
- 200-period EMA
- Supertrend (Parameters: ATR Period=10, Multiplier=3)

## Timeframe Compatibility (scalp / swing / position)
- **Swing:** 4H and 1H timeframes (Primary)
- **Scalp:** 15m (Requires tighter EMA filter like 100 EMA)

## Theoretical Risk — what market conditions break this strategy?
- **Choppy/Sideways Markets:** Frequent "whipsaws" where Supertrend flips back and forth while price remains stuck in a range, leading to multiple small losses.
- **V-Shaped Recoveries:** The 200 EMA is lagging; during a sharp reversal from a bear market, the price may move significantly higher before the EMA filter allows a long entry.

## Source — URL or reference
https://www.binance.com/en/blog/trading/how-to-use-the-supertrend-indicator-421499824684903342

## Interest Rating — [High] with one-line reason
High - Provides clear binary states (Trend/Signal) and accounts for BTC volatility, making it an ideal candidate for DRL state-space mapping.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/SuperTrend]]
