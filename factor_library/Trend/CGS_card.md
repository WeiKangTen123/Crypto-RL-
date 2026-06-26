---
name: Choppiness-Gated Supertrend (CGS)
category: Trend
coins: [BTC, ETH, BNB, SOL, XRP]
timeframes: [4h]
status: IMPLEMENTED
---

## Alpha Premise
Supertrend is an excellent trend-following indicator but suffers heavy drawdowns during ranging markets. By gating the entry using the Choppiness Index (CHOP < 38.2) we only enter Supertrend flips when a directional regime is mathematically confirmed.

## Strategy Play Style
Volatility Breakout & Pure Trend. This explicitly aims to capture massive multi-day structural trends while remaining completely flat during sideways chop.

## Strategic Disadvantages
Missing the initial leg of a trend. The Choppiness Index takes time to fall below the 38.2 threshold, meaning the strategy enters a breakout slightly late but with higher mathematical certainty.

## Enhancement Recommendations
1. Use `calc_choppiness_index` and `calc_supertrend` directly from `library.py`.
2. Consider adding an ADX threshold (e.g., >25) to double-confirm the CHOP index reading.

## Agent Reasoning (Chain of Thought)
Poison Filter Activation: `scan_results.json` reveals that `SupertrendProStrategy` and `SupertrendATRMomentumStrategy` failed miserably (e.g., ID 20: Sharpe 0.15, Win Rate 33%). Autopsy dictates that pure Supertrend gets slaughtered in ranging markets. To fix this, I engineered a gate: We only accept a 4H Supertrend flip IF the Choppiness Index is < 38.2 (indicating a mathematically verified non-ranging regime). This transforms a failing strategy into a high-conviction MFT alpha.
