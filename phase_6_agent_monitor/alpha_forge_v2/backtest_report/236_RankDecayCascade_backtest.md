# Backtest Report: 236_RankDecayCascade

## 1. Strategy Identity
- **ID:** `236`
- **Class:** `RankDecayCascade`
- **Type:** "HARD" WorldQuant Alpha 31
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `rank(decay_linear(-1 * rank(delta(close, 10)), 10)) + rank(-1 * delta(close, 3))`
- **Smooth Long Fade:** Calculates the 10-period momentum and fades it (multiplies by -1 to seek mean reversion). It applies a 10-period linear decay to this fade, effectively creating a heavily smoothed, time-weighted measurement of the recent drop. It then takes the cross-sectional rank of this smoothed vector.
- **Raw Short Fade:** Calculates the raw 3-period momentum and immediately fades it. It ranks this short-term snapback vector.
- **Alpha Synthesis:** It adds both ranks together, producing a final score between `0.0` and `2.0`. This forces the strategy to hunt for coins that are *both* undergoing a prolonged, steady 10-period bleed *and* just suffered a sharp 3-period raw washout.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values.

## 4. Analysis and Next Steps
- **Baseline:** The baseline scan is currently running.
- **Optuna Tuning Results:** Optuna is exploring the optimal combination of heavily smoothed long-fades vs raw short-fades to see if the sum of two separate timeframe ranks produces an elite signal.
