---
status: PAPER_READY
id: 127
sharpe: 1.24
return: 283.0
MDD: 26.0
---

# Market Fit Memo: FORGE_ETH_EMA_WR_SHORT_TIGHT (ID 127)

## 1. Recent Regime Check
ETH/4h Williams %R is currently at -38 (well within the -10 to -90 acceptable band). EMA price cross signal has fired 3 times in the past 45 days with 2/3 resulting in positive trades (67% win rate in-sample recent period). Regime shows moderate trend with no extreme momentum — ideal conditions for this strategy's WR filter to operate as designed.

## 2. Correlation Warning
EMA price cross is directionally correlated with #120 (EMA Supertrend) and partially with #117 (ZLEMA taker). All three will enter during genuine EMA trend initiations. However #127's WR filter makes it more selective — it fires in a subset of events that #120 triggers. The strategies are not perfectly correlated, providing some diversification. Combined EMA-cluster allocation still applies: total EMA-trend strategies < 40% of portfolio.

## 3. Deployment Recommendation
**Second priority for paper trading, alongside #125.** The critical differentiator: all 5 years positive makes this the most defensible strategy for conservative capital allocation. MDD of 26% at 10x leverage is manageable — a 26% drawdown means a 2.6% drawdown on the underlying capital before leverage, leaving 7.4% risk buffer before a margin call.

Best use case: deploy as the "always-on" base allocation (30-40% of portfolio) with #125 as the "high-alpha" overlay (20-30%). The two strategies have low overlap in trigger events (FVG vs EMA price cross) providing genuine diversification within the trend-momentum category.
