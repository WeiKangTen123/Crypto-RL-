---
name: Zero-Lag Volatility Expansion (ZVE)
category: Volatility_Breakout
coins: [ETH, SOL, BTC, BNB, XRP]
timeframes: [1h, 15m]
author: alpha-researcher
status: IMPLEMENTED
---

# Zero-Lag Volatility Expansion (ZVE)

## Strategy Premise
A high-frequency (Medium-Frequency, ~1h) volatility expansion system that relies on zero-lag momentum (DEMA-based MACD) and Volume-Weighted Moving Average (VWMA) crosses to identify and validate Keltner Channel breakouts.

## Market Mechanics
Traditional oscillators (like standard MACD or EMA) lag significantly, causing entries to occur at the top of a breakout wick, leading to immediate drawdowns. The Zero-Lag MACD (`calc_zero_lag_macd`) removes this latency. When combined with Keltner Channels, it spots the exact moment momentum transitions from compression to trend, and the VWMA vs EMA comparison acts as a volume profile verification.

## Mathematical Model
- **Breakout Metric:** Close > Upper Keltner Channel (`calc_keltner_channels(period=20, mult=2.0)`).
- **Momentum Confluence:** `calc_zero_lag_macd` fast line crosses above the signal line (or is strongly positive > 0).
- **Volume Confluence:** `calc_vwma(period=20)` > `calc_ema(period=20)` (Volume is trading at higher prices).
- **Compression Filter:** `calc_choppiness_index(period=14)` recently > 61.8 (within last 10 bars), currently dropping below 50.
- **Exit Logic:** Opposite crossing of ZMACD or trailing SuperTrend.

## Strategy Play Style
Precision Trend-Following Breakout. It excels at entering trends very early in the cycle, capturing the "meat" of the move with minimal lag. 

## Strategic Disadvantages
In hyper-volatile, non-directional chop (wide ranges), the zero-lag nature might be *too* reactive, triggering entries on sudden liquidity sweeps before quickly reversing. 

## Enhancement Recommendations
1. For Developer: Use `calc_supertrend` as the primary trailing stop to give the trade room to breathe on the 1h timeframe, avoiding premature exits on 1h wicks.
2. For Tuner: Tune the Keltner Channel multiplier (`mult`) between 1.5 and 2.5. A lower multiplier increases the trade frequency to comfortably exceed the 350+ floor.

## Agent Reasoning (Chain of Thought)
- **Why 1h Timeframe?** To hit the strict frequency floor of 1 trade every 2-3 days (350+). 
- **Why this fixes AVS_BTC_4H poison:** AVS used Fisher and VRSI, failing to filter out choppy false breakouts. ZVE addresses this by demanding *both* a structural compression reset (Choppiness > 61.8) and a volume distribution confirmation (VWMA > EMA). The ZMACD ensures the entry isn't late, protecting the Sharpe ratio.
