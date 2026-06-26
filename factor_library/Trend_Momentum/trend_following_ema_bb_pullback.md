## Strategy Name
Trend-Following EMA & Bollinger Band Pullback

## Category
Trend Following (momentum, breakout, moving average crossover)

## Core Hypothesis — WHY should this strategy have an edge?
The strategy exploits the "trend persistence" and "mean reversion within a trend" behaviors of Bitcoin. In a strong trending market, price often overextends and then pulls back to a value area (the lower band in an uptrend) before continuing the primary move. By using a 50 EMA as a regime filter, we ensure we are trading with the dominant momentum. The Bollinger Band touch identifies a temporary exhaustion of the counter-trend move, and the RSI confirmation ensures we aren't catching a "falling knife" but rather entering when momentum is starting to rotate back in favor of the trend.

## Entry Signal — exact condition that triggers a buy
**Long Entry:**
1. **Regime Filter:** Price must be trading **above** the 50-period Exponential Moving Average (EMA).
2. **Pullback:** Price touches or breaks below the **Lower Bollinger Band** (20, 2).
3. **Momentum Confirmation:** RSI (14) is below 30 (oversold) or shows a bullish divergence on the entry timeframe.
4. **Trigger:** Enter on the close of the first candle that closes back **inside** the Bollinger Bands, provided it is a bullish candle (close > open).

**Short Entry:**
1. **Regime Filter:** Price must be trading **below** the 50-period EMA.
2. **Pullback:** Price touches or breaks above the **Upper Bollinger Band** (20, 2).
3. **Momentum Confirmation:** RSI (14) is above 70 (overbought) or shows a bearish divergence.
4. **Trigger:** Enter on the close of the first candle that closes back **inside** the Bollinger Bands, provided it is a bearish candle (close < open).

## Exit Signal — exact condition that triggers a sell or position close
1. **Primary Target (Take Profit):** Opposite Bollinger Band (Upper for Longs, Lower for Shorts).
2. **Secondary Target:** 2.0 Risk-to-Reward ratio based on the stop loss.
3. **Stop Loss:** Placed 0.5% below the recent swing low (for Longs) or 0.5% above the recent swing high (for Shorts).
4. **Time Exit:** If the price hasn't reached the target or stop within 24 bars, close manually (to avoid "dead money" in consolidating markets).

## Key Indicators / Data Required
- **Price Data:** OHLCV (Open, High, Low, Close, Volume)
- **50 EMA:** Exponential Moving Average (Period 50)
- **Bollinger Bands:** (Period 20, StdDev 2)
- **RSI:** Relative Strength Index (Period 14)

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** 15-minute and 1-hour (Intraday/Daily trading frequency).
- **Compatibility:** Scalp (5m) to Swing (4h).

## Theoretical Risk — what market conditions break this strategy?
1. **Chop/Sideways Markets:** In a non-trending market, the price will frequently cross the 50 EMA, leading to "whipsaws" where the pullback signal is triggered but the trend fails to continue.
2. **V-Reversals:** Rapid, news-driven trend reversals will hit stops as the "pullback" becomes the start of a new opposite trend.
3. **Low Volatility Squeezes:** When Bollinger Bands are very narrow, "touches" are less meaningful and signals become noisy.

## Source — URL or reference
Derived from common institutional "Trend-Following Pullback" setups and verified via multiple crypto trading educator frameworks (e.g., TradingPedia, Binance Academy).

## Interest Rating — [High] with one-line reason
High - This strategy provides a perfect balance of trend-following and mean-reversion, making it an excellent candidate for a DRL reward signal (rewarding entries near the lower band in an uptrend).

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/Bollinger_Bands]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]
