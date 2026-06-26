---
status: PAPER_READY
id: 120
sharpe: 1.49
return: 498.0
MDD: 36.8
---

# Market Fit Memo: FORGE_ETH_EMA_SUPERTREND (ID 120)

## 1. Recent Regime Check
ETH/4h Supertrend is currently in bullish configuration (price above Supertrend line). EMA fast has been above EMA slow for the last 14 bars. Regime is highly aligned with this strategy's optimal conditions: sustained directional trend with expanding ATR. Strategy is actively generating entries in current market.

## 2. Correlation Warning
EMA crossover entry shares directional factor with all other EMA-based strategies (#127 EMA price cross, #119 RSI + EMA trend). In a correlated drawdown (e.g., ETH flash crash), all EMA strategies will be simultaneously stopped out. Portfolio allocation should treat all EMA-trend strategies as a single factor cluster — total combined allocation should not exceed 40% of portfolio.

## 3. Deployment Recommendation
Highest Sharpe in V2 batch (1.49) — top priority for paper trading alongside #125. The Supertrend trail is visually easy to monitor (single line on chart). Set automated alerts for Supertrend flip events. The strategy is one of two V2 candidates recommended for immediate paper trading deployment.
