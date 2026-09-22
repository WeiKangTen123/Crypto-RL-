---
coins:
- BTC
- ETH
- BNB
- SOL
- XRP
status: IN_PROGRESS
tags:
- in_progress
timeframes:
- 4h
- 1d
type: Cross_Sectional
---
# Cross-Sectional Relative Momentum Ranking

**MULTI-COIN PORTFOLIO** strategy

## Alpha Premise
In the cryptocurrency market, assets often move in tandem due to high beta to Bitcoin. However, cross-sectional momentum exploits the relative dispersion between altcoins. By ranking a basket of top-tier assets (BTC, ETH, BNB, SOL, XRP) by their intermediate-term returns (e.g. 14 to 30 bars), we can identify which assets are accumulating the most institutional flow and which are lagging or being actively distributed. We go long the top performer(s) and short the bottom performer(s) to create a market-neutral or directional-hedge portfolio.

## Strategy Play Style
- **Market Neutral / Pairs Trading**: Aims to hedge out the broader market beta by simultaneously holding long and short positions.
- **Trend Dispersion**: Excels in environments where capital rotates between specific Layer-1 chains (e.g., Solana outperforming while Ethereum lags).

## Strategic Disadvantages
- **Correlated Crashes**: If the entire market drops instantly (e.g., a systemic crypto liquidation event), correlation goes to 1.0, and the short position may not hedge the long position adequately due to varied drawdowns.
- **Whipsaws**: Choppy, trendless markets where yesterday's top performer becomes tomorrow's bottom performer.

## Enhancement Recommendations
- **Volatility Scaling**: Instead of using raw return for ranking, use Sharpe ratio or Return / ATR (volatility-adjusted momentum) to rank the assets.
- **Regime Filter**: Only deploy the short side if the broad market trend (BTC) is bearish, or only deploy the long side if the broad market is bullish.

## Agent Reasoning (Chain of Thought)
1. **Factor Math**: We need to calculate `ROC(period)` or `Close / Close[period] - 1` for all assets.
2. **Ranking**: On each bar, rank the assets from 1 to N based on the ROC.
3. **Signal Generation**:
   - `Signal = 1` for the asset with Rank 1 (Top performer).
   - `Signal = -1` for the asset with Rank N (Bottom performer).
   - `Signal = 0` for everything else.
4. **Execution**: The `PortfolioBacktestEngine` will ensure we short the weakest and buy the strongest.
5. **Minimum History**: Requires at least 2 years of data to test stability across different crypto cycles. 

Minimum history: 2 years
