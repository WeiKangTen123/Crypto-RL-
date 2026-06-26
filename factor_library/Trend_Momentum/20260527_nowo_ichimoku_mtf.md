---
coins: BTC, ETH, SOL, BNB, XRP
interest: High
name: nowo-ichimoku-mtf
source: Freqst / NowoIchimoku5mV2
status: QUEUED
tags:
- queued
timeframes: 5m, 1h
type: short-term
---
# Nowo Ichimoku MTF

## Concept
Uses Ichimoku Cloud on a 5m timeframe for entry signals, but filters them based on a 1h "informative" Ichimoku trend. This reduces noise and ensures trading in the direction of the macro momentum.

## Entry Conditions
- Long:
    1. 5m Close > 5m Kumo Cloud.
    2. 5m Tenkan-sen > 5m Kijun-sen.
    3. 1h Close > 1h Kumo Cloud (Trend Filter).
- Short:
    1. 5m Close < 5m Kumo Cloud.
    2. 5m Tenkan-sen < 5m Kijun-sen.
    3. 1h Close < 1h Kumo Cloud (Trend Filter).

## Exit Conditions
- Take profit: 2:1 RR or when 5m Close crosses back through the Cloud.
- Stop loss: Below/above the 5m Kijun-sen or ATR-based.

## Key Indicators
- Ichimoku Cloud (9, 26, 52, 26)
- MTF Informative Pairs (1h)

## Expected Edge
Combines a proven momentum/trend indicator (Ichimoku) with a multi-timeframe filter to avoid "whipsaws" in lower timeframes. High liquid crypto markets respond well to Ichimoku levels.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 5m
- Minimum history: 1 year

## Implementation Notes
- Requires handling of multiple timeframes in the backtester.
- Ichimoku calculations need to be precise (Senkou Span A/B shifts).

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
