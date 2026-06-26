## Strategy Name
Cross-Asset Macro Lead-Lag Regime Filter

## Category
Macro / Cross-Asset

## Core Hypothesis — WHY should this strategy have an edge?
Bitcoin is widely considered a "Risk-On" asset. Because it trades 24/7, it often acts as a liquidity valve for global markets. However, the true directional trend is often established by the "Motherships": the S&P 500 (SPY) and the US Dollar Index (DXY). On a daily timeframe, BTC frequently lags behind major shifts in equity indices or currency strength. By analyzing the "Lead-Lag" relationship, we can establish a "Safe-to-Trade" regime. If SPY is trending up and DXY is trending down, BTC has a structural tailwind that increases the probability of any long entry.

## Entry Signal — exact condition that triggers a buy
1. **Equity Lead:** SPY (or ES Futures) closes at a new 5-day high.
2. **Currency Lead:** DXY closes at a new 5-day low.
3. **BTC Signal:** Look for any bullish price action (e.g., 1h EMA cross) on BTC during the first 4 hours of the next day.
**Logic:** We are using the 1d lead signal to filter for high-probability 1h/4h entries.

## Exit Signal — exact condition that triggers a sell or position close
1. **Regime Change:** Exit all longs if SPY closes below its 20-day SMA or DXY breaks its 20-day downtrend line.
2. **Profit Target:** Fixed 5% gain or exit at previous monthly high.

## Key Indicators / Data Required
- **SPY Daily Close**
- **DXY Daily Close**
- **BTC 1d/4h/1h OHLCV**

## Timeframe Compatibility (scalp / swing / position)
- **1d:** Regime identification.
- **4h / 1h:** Trade execution.

## Theoretical Risk — what market conditions break this strategy?
"Decoupling" events where BTC crashes despite a strong stock market (e.g., industry-specific black swans like exchange hacks or regulatory crackdowns).

## Source — URL or reference
- Research on "Intermarket Analysis" by John Murphy.
- Quantitative papers on "Crypto-Equity Correlation" during Risk-On regimes.

## Interest Rating — [Medium-High]
High — This provides the DRL agent with "Global Context." An agent that only looks at BTC is blind to the macroeconomic forces that actually move the market.

---
## Connections

**Category:** [[Cross_Sectional/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/SMA]]
