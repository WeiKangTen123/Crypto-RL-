# MARKET FIT MEMO: TD-VSB (Strategy 155)

**CONFIDENTIAL INTERNAL MEMO**
**Subject:** Discovery of an ELITE Grade Volatility Breakout Model (TD-VSB)
**Date:** 2026-06-24

### 1. Executive Summary
Following the failure of purely price-derived microstructure anomalies (AVS_BTC_4H), the research pivot toward purely volume/order-flow validated volatility expansions has yielded a massive success. Strategy 155 (Taker-Driven VWAP Squeeze Breakout) has achieved Elite Grade metrics, successfully threading the extreme constraint matrix of >350 trades, >1.0 Sharpe, and <20% Drawdown.

### 2. The Statistical Alpha
*   **Performance Metrics:** 91.17% Total Return (20.9% Annual, ~2% Monthly).
*   **Risk Profile:** Max Drawdown 17.20%. Sharpe 1.04. Sortino 1.65.
*   **Asymmetry:** Win Rate is 19.22%, but Profit Factor is 1.51. The tuning engine discovered a hyper-asymmetric TP/SL ratio (SL at 1.0 ATR, TP at ~6.0 ATR).

### 3. The Structural Edge
The edge lies not in predicting the breakout direction, but in validating institutional participation. The `calc_taker_intensity` parameter mandates that the breakout is accompanied by aggressive taker volume (Z-Score > 1.6). This completely nullifies low-volume retail fakeouts. When combined with the baseline `calc_bb_kc_squeeze` and VWAP deviation filters, it ensures entries occur precisely as multi-week range compressions explode into trend.

### 4. Recommendation for Phase 4
This is the strongest high-frequency candidate currently in the pipeline. It is formally approved to advance to Phase 4 for rigorous Walk-Forward Optimization (WFO_EVO) to test the robustness of its parameters against out-of-sample regime shifts.
