# Hypothesis Report: Zero-Lag Volatility Expansion (ZVE)

**Date:** 2026-06-24
**Strategy Name:** ZVE (1H)
**Author:** alpha-researcher
**Category:** Volatility_Breakout

## 1. Core Hypothesis
We hypothesize that a Keltner Channel Breakout validated by a Zero-Lag MACD (`calc_zero_lag_macd`) and a Volume-Weighted Moving Average cross (`calc_vwma` > `calc_ema`) will provide early and precise entries into volatility expansions. On the 1H timeframe, this system will generate >350 trades with a Sharpe > 1.0 by eliminating the latency inherent in traditional MACD/EMA signals, effectively capturing the bulk of medium-frequency trends.

## 2. Rationale & Poison Control
The autopsy of AVS_BTC_4H revealed that sluggish exits and late entries compounded losses during chop. The Zero-Lag Volatility Expansion directly addresses this by using DEMA-based MACD to completely remove mathematical lag. Furthermore, the volume profile is validated not by an oscillator, but by ensuring the VWMA trades at a premium to the standard EMA, confirming upside volume distribution. 

## 3. Implementation Blueprint
- **Timeframe:** 1H
- **Assets:** ETH, SOL, BTC, BNB, XRP
- **Indicators:**
  - `calc_choppiness_index(df, period=14)` (Filter)
  - `calc_keltner_channels(df, period=20, mult=2.0)` (Breakout)
  - `calc_zero_lag_macd(df)` (Momentum)
  - `calc_vwma(df, period=20)` & `calc_ema(df, period=20)` (Volume Confluence)
