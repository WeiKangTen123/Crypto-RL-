---
name: Hammer Volume Exhaustion Reversion (HVE)
status: IMPLEMENTED
coins: [SOL, ETH, XRP]
timeframes: [4h]
author: alpha-researcher
---
## Alpha Premise
Extreme panic selling often culminates in a "capitulation" candle with a long lower wick (Hammer/Pin Bar) accompanied by a massive volume spike. By combining Donchian Channel extremes, Volume-Weighted RSI (VRSI) exhaustion, and the Hammer candlestick pattern, we can identify high-probability mean-reversion bounces.

## Strategy Play Style
Contrarian / Mean Reversion. Best suited for high-volatility flush-outs and flash crashes.

## Strategic Disadvantages
Protracted "waterfall" sell-offs where multiple hammers form and fail consecutively.

## Enhancement Recommendations
1. Add a Z-score filter for Volume (e.g., Volume > 2 standard deviations) to ensure true capitulation.
2. Use the middle Donchian Channel or middle Bollinger Band as a dynamic Take Profit level.

## Agent Reasoning (Chain of Thought)
- **Extreme Extension**: Close price must be interacting with the lower Donchian Channel (20-period).
- **Volume Exhaustion**: `calc_vrsi(14)` must be < 25, indicating severe downward volume pressure is maxed out.
- **Candle Trigger**: `detect_candle_hammer()` must evaluate to True on the current or previous bar.
- **Exit**: Price reverts to the Middle Donchian Channel. Stop Loss at the low of the Hammer candle - 1% buffer.
- **Library Match**: `calc_donchian_channels`, `calc_vrsi`, `detect_candle_hammer`.
