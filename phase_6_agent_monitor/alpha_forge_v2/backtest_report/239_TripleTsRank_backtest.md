# Backtest Report: 239_TripleTsRank

## 1. Strategy Identity
- **ID:** `239`
- **Class:** `TripleTsRank`
- **Type:** "YES-MEDIUM" WorldQuant Alpha 35
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `((ts_rank(volume, 32) * (1 - ts_rank(((close + high) - low), 16))) * (1 - ts_rank(returns, 32)))`
- **Volume Exhaustion:** Uses `ts_rank(volume)` to demand that the current volume is extremely high relative to recent history.
- **Intraday Selling Pressure:** Uses `1 - ts_rank(close + high - low)` to demand that the intraday buying pressure (where the close is relative to the high-low range) is at its historical minimum.
- **Price Exhaustion:** Uses `1 - ts_rank(returns)` to demand that the actual bar return is at its historical minimum.
- **The Alpha Trigger:** It multiplies these three ranks (each bounded between 0.0 and 1.0) together. A buy signal only triggers when the product approaches 1.0, which only happens if all three conditions are simultaneously met. This is a classic, pure-math exhaustion capitulation signal.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values. (NOTE: 3% SL removed from grid).

## 4. Analysis and Next Steps
- **Optuna Tuning Results:** The optimizer found a heavily skewed timeframe alignment (`vol_p: 15`, `bp_p: 50`, `ret_p: 100`) to maximize the edge, resulting in a **`0.57` Sharpe Ratio** and **`108.3%` Return** over 834 trades. 
- **Conclusion:** While it generated a solid ROI, the Sharpe ratio sits squarely in the MEDIOCRE tier. This confirms our hypothesis: strict traditional quant mean-reversion signals struggle to reach elite (>1.0) risk-adjusted metrics on 4-hour crypto datasets unless they are allowed to overfit to tiny 3% noise-scalp stops.
