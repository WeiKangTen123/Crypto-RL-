# Hypothesis Report: Taker-Driven VWAP Squeeze Breakout (TD-VSB)

**Date:** 2026-06-24
**Strategy Name:** TD-VSB (1H)
**Author:** alpha-researcher
**Category:** Volatility_Breakout

## 1. Core Hypothesis
We hypothesize that by requiring a high Taker Intensity (`calc_taker_intensity` > 1.25) during a VWAP Z-Score breakout (`calc_vwap_zscore` > 1.5) out of a Bollinger/Keltner Squeeze (`calc_bb_kc_squeeze`), we can capture high-momentum volatility expansions while filtering out the false breakouts that poisoned the AVS_BTC_4H strategy. This structure is projected to hit a 1H trade frequency of >350 over 3.4 years while retaining a Sharpe > 1.0 and keeping MDD ~20%.

## 2. Rationale & Poison Control
The AVS_BTC_4H strategy failed due to reliance on derivative oscillators (VRSI/Fisher) in choppy markets. By substituting raw order flow intensity (Taker volume vs Total volume) and standardizing the breakout metric against the dynamic fair value (VWAP), we isolate institutional momentum. The shift from 4H to 1H timeframe guarantees sufficient sample size to meet the >350 trades criteria without degrading the signal-to-noise ratio.

## 3. Implementation Blueprint
- **Timeframe:** 1H
- **Assets:** BTC, ETH, SOL, BNB, XRP
- **Indicators:**
  - `calc_bb_kc_squeeze(df, bb_period=20, kc_period=20)`
  - `calc_vwap_zscore(df, period=20)` 
  - `calc_taker_intensity(df, period=24)`
  - `calc_chandelier_exit(df)`
