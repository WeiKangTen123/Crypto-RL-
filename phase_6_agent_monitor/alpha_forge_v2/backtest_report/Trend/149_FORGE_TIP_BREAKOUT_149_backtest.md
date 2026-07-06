# Alpha Forge V2 Backtest Report
**Strategy ID:** TIP_BREAKOUT_ETH_1H_149
**Registry ID:** 149
**Date:** 2026-06-24
**Coin/Timeframe:** ETH / 1h (2023-01-01 to 2026-06-01)

## 1. Strategy Architecture
- **Class:** `TIPBreakoutStrategy` (Standalone)
- **Description:** Taker-Intensity Participation (TIP) Breakout. 
- **Core Algorithm:** Requires price closing above upper BB AND taker buy ratio > threshold AND trade intensity > z-score threshold.
- **Risk Mechanic:** Stop-Loss and Take-Profit are locked dynamically using ATR at the exact time of entry, ensuring non-repainting stable exit logic.

## 2. Risk Management
- **Initial Balance:** $10,000
- **Risk Per Trade:** 5%
- **Leverage:** 5x
- **Trading Fee:** 0.04%

## 3. Tuned Parameters (Optuna 75 Trials)
- `bb_period`: 24
- `bb_std`: 2.17
- `intensity_period`: 19
- `intensity_std`: 1.59
- `taker_threshold`: 0.54
- `sl_atr_mult`: 0.51
- `tp_atr_mult`: 7.41
- `max_hold_bars`: 133

## 4. Performance Metrics
- **Total Return:** 21.92%
- **Sharpe Ratio:** 0.880
- **Max Drawdown:** 8.72%
- **Win Rate:** 21.6%
- **Total Trades:** 801

## 5. Developer Notes
The strategy was migrated out of the Forge to function as a standalone class, strictly importing logic from `library.py`. Decoupling from the Forge allowed for stable, locked-at-entry ATR stops instead of floating stops. 

A fresh Optuna scan yielded a dramatically healthier performance profile. By reducing the `intensity_std` requirement from 2.48 to 1.59 and the `taker_threshold` to 0.54, the strategy generated 801 trades (vs 30 previously) over 3.5 years. Total returns rose from 7.8% to 21.9% while maintaining an excellent 0.880 Sharpe ratio. The strategy's risk profile heavily relies on catching large asymmetric breakouts, as evidenced by the 21.6% win rate but massive 7.41x ATR take-profit multiplier.
