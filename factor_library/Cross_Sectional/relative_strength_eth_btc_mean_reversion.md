## Strategy Name
ETH/BTC Ratio Statistical Mean Reversion

## Category
Relative Strength (ETH/BTC ratio, statistical arbitrage)

## Core Hypothesis — WHY should this strategy have an edge?
The ETH/BTC ratio represents the relative valuation between the two largest crypto assets. While they are highly correlated (0.8+), they often diverge intraday due to asset-specific news, ETF flow imbalances, or differing leverage profiles. Statistically, the ratio tends to be mean-reverting over short timeframes (15m to 1h) because market participants eventually arbitrage away extreme relative overvaluation/undervaluation. This strategy exploits "over-extensions" in the ratio by betting on a return to the daily mean.

## Entry Signal — exact condition that triggers a buy
**Long ETH / Short BTC (Ratio Buy):**
1. **Timeframe:** 1-hour OHLCV from both `/dataset/BTC/1h` and `/dataset/ETH/1h`.
2. **Indicator:** Z-Score of the ETH/BTC ratio relative to its 20-period moving average.
3. **Condition:** Z-Score drops below **-2.5** (Ratio is 2.5 standard deviations below its mean).
4. **Trigger:** Enter when the ratio shows a bullish reversal candle (e.g., hammer) on the 15m timeframe while the 1h Z-score is still in the "Buy Zone".

**Short ETH / Long BTC (Ratio Sell):**
1. **Indicator:** Z-Score of the ETH/BTC ratio.
2. **Condition:** Z-Score rises above **+2.5**.
3. **Trigger:** Enter when the ratio shows a bearish rejection candle on the 15m timeframe.

## Exit Signal — exact condition that triggers a sell or position close
1. **Primary Target:** The mean (Z-Score = 0).
2. **Secondary Target:** The opposite Z-Score band (e.g., if entered at -2.5, exit at +1.0).
3. **Stop Loss:** If the Z-Score continues to expand to **-4.0** (signaling a fundamental regime shift or "decoupling"), exit immediately to preserve capital.
4. **Time Exit:** If the mean isn't reached within 24 hours, close the position (avoiding overnight risk in volatile regimes).

## Key Indicators / Data Required
- **BTC & ETH Price Data:** Synchronized 15m and 1h OHLCV.
- **Ratio Calculator:** (ETH Price / BTC Price).
- **Z-Score Indicator:** Standard Deviation and Moving Average of the ratio.

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** Intraday (15m execution / 1h context).
- **Frequency:** High (1-3 setups per week).

## Theoretical Risk — what market conditions break this strategy?
1. **Regime Decoupling:** Large asset-specific events (e.g., ETH Shanghai upgrade, BTC Spot ETF approval) can cause the ratio to "trend" for days, making mean reversion a losing bet.
2. **Low Correlation Environments:** If BTC and ETH stop moving together, the "mean" becomes a moving target.
3. **Liquidation Cascades:** A massive long squeeze in ETH can drive the ratio far beyond statistical norms.

## Source — URL or reference
Commonly used by crypto market makers and quantitative arbitrageurs; updated for the 2024-2026 ETF flow environment.

## Interest Rating — [High] with one-line reason
High - This is a classic "active" strategy that provides a hedge against broad market movements while profiting from relative mispricings.

---
## Connections

**Category:** [[Cross_Sectional/_Index]]
