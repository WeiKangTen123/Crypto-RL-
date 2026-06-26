---
name: McGinley Dynamic Volume Breakout (MDVB)
status: IMPLEMENTED
coins: [BTC, ETH, SOL]
timeframes: [4h]
author: alpha-researcher
---
## Alpha Premise
Traditional moving averages often suffer from lag and whipsawing in high-volatility crypto markets. The McGinley Dynamic indicator continuously adjusts its smoothing factor based on market speed, reducing false signals. By combining it with a Volume-Weighted RSI (VRSI) and the Choppiness Index, we filter out range-bound noise and enter high-probability momentum breakouts.

## Strategy Play Style
Aggressive Trend-Following Breakout. Best suited for prolonged trending regimes and expansion phases.

## Strategic Disadvantages
Choppy, low-volatility environments (even with the filter, sudden macro spikes can trigger false breakouts).

## Enhancement Recommendations
1. Add an ADX threshold gate (e.g., ADX > 20) alongside Choppiness to double-confirm trend strength.
2. Implement a volatility-based trailing stop (e.g., Chandelier Exit) instead of relying solely on the faster McGinley line.

## Agent Reasoning (Chain of Thought)
- **Trend**: Close price must be above McGinley Dynamic (50-period).
- **Filter**: Choppiness Index (14) must be < 38.2 to confirm we are NOT in a sideways range.
- **Trigger**: VRSI (14) crosses above 50, showing that volume is actively supporting the upward price action.
- **Exit**: Close falls below a faster McGinley Dynamic (20-period) indicating momentum loss.
- **Library Match**: `calc_mcginley_dynamic`, `calc_choppiness_index`, `calc_vrsi`.
