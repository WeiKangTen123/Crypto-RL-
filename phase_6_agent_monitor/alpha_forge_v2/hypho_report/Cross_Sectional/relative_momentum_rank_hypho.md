# Alpha Forge Hypothesis: Cross-Sectional Relative Momentum Ranking

**Date**: 2026-07-06
**Category**: Cross_Sectional
**Coins**: BTC, ETH, BNB, SOL, XRP (MULTI-COIN PORTFOLIO)
**Timeframes**: 4h, 1d

## 1. The Anomaly (Alpha Source)
Cryptocurrency capital rotates. During bull markets, liquidity flows from Bitcoin to large-cap altcoins, then to mid-caps. By tracking the relative performance of the top 5 most liquid tokens, we can systematically capture this rotation. A token outperforming the rest of the basket implies localized capital inflows, while the lagging token suffers from outflows or dilution.

## 2. The Hypothesis
**H1**: A cross-sectional ranking strategy that goes long the highest momentum asset and short the lowest momentum asset will generate a positive alpha with lower market beta than a buy-and-hold BTC portfolio.

## 3. Mathematical Model
- Let $R_{i,t}$ be the return of asset $i$ over the past $N$ periods.
- Rank assets at time $t$ such that $Rank_1$ is the highest $R_{i,t}$ and $Rank_5$ is the lowest.
- Signal: $w_{1} = 1.0$, $w_{5} = -1.0$, all other $w = 0$.

## 4. Execution Plan
- The strategy will be implemented as a `MultiCoinBaseStrategy`.
- `PortfolioBacktestEngine` will execute trades on the aligned multi-coin data, utilizing the shared cross-margin account balance to ensure accurate margin calculations and combined portfolio tracking.
