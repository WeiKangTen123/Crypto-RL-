---
name: Taker-Driven VWAP Squeeze Breakout (TD-VSB)
category: Volatility_Breakout
coins: [BTC, ETH, SOL, BNB, XRP]
timeframes: [1h, 15m]
author: alpha-researcher
status: IMPLEMENTED
---

# Taker-Driven VWAP Squeeze Breakout (TD-VSB)

## Strategy Premise
This strategy resolves the failure of previous adaptive squeeze models (like AVS_BTC_4H) by mandating that a volatility expansion must be validated by aggressive, market-order order flow and a significant standard-deviation deviation from the VWAP. 

## Market Mechanics
During consolidation phases (Squeeze), liquidity builds up. Retail traders place stops around the edges of the consolidation. When a breakout occurs, institutional players drive price using aggressive "taker" market orders. By ensuring that `taker_intensity` > threshold concurrently with a VWAP Z-Score breakout, we avoid "fakeouts" and chop-market whipsaws.

## Mathematical Model
- **Consolidation Filter:** `calc_bb_kc_squeeze` == True in the recent `N` periods.
- **Breakout Metric:** `calc_vwap_zscore(period=20)` crossing above +1.5 (Long) or below -1.5 (Short).
- **Order Flow Confluence:** `calc_taker_intensity(period=24)` must be > 1.25.
- **Exit Logic:** `calc_chandelier_exit` or when VWAP Z-score reverts back to 0.

## Strategy Play Style
Aggressive Momentum Breakout. Designed to capture explosive, high-intensity moves immediately following periods of range-bound compression. It performs exceptionally well in fast-trending crypto environments where volume spikes are localized.

## Strategic Disadvantages
Vulnerable during low-liquidity weekends or "slow bleeds" where price trends steadily but without high taker intensity, causing the strategy to miss the move entirely. 

## Enhancement Recommendations
1. For Developer: Use `window_any_true` on the squeeze signal to allow a 3-5 bar window for the breakout to materialize after the squeeze fires.
2. For Tuner: Optimize the `taker_intensity` standard deviation threshold tightly. If set too high, it will miss trades. 

## Agent Reasoning (Chain of Thought)
- **Why 1h Timeframe?** To achieve the required >350 trades over 3.4 years. 4H timeframes do not generate enough distinct compression/expansion cycles to meet the trade floor.
- **Why this fixes AVS_BTC_4H poison:** The previous model used VRSI and Fisher, which are derivative oscillators. They misfired in chop. Taker intensity is a primary data source derived directly from `taker_buy_base_vol` and `num_trades`, meaning it relies on actual executed aggressive volume, eliminating low-volume fakeouts.
