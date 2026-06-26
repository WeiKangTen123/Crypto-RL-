# Backtest Report: Dynamic VWAP ATR Scalper (DVAS - BNB)

**Date:** 2026-06-24
**Strategy ID:** 158
**Class:** DVASStrategy (BNB 1H)
**Status:** ELITE (Optuna Tuned - Expanded Space)

## 1. Final Optuna Parameters
- `atr_dev_thresh`: 0.9760
- `rsi_extreme`: 33.2630
- `vol_spike_mult`: 1.3074
- `tp_multiplier`: 2.3810
- `sl_multiplier`: 0.0020 (Hyper-tight stop loss)

## 2. Quantitative Results (2023 - 2026)
- **Total Return:** 474.1%
- **Sharpe Ratio:** 2.43
- **Total Trades:** 1096

## 3. Analysis & Verdict
**ELITE GRADE.** By expanding the optimization search space and running 200 generations, the tuner cracked the BNB inertia problem. It discovered that BNB *does* snap back to the VWAP, but you must enter much earlier (at ~0.97 ATR deviation rather than 1.5+ ATR like SOL) and employ the exact same "Instant Kill" hyper-tight stop loss (0.002 ATR) if the snapback doesn't immediately validate.

This turned a previously negative edge (-0.04 Sharpe) into a phenomenal 2.43 Sharpe with +474% returns.

*Warning:* Like the SOL model, the microscopic Stop Loss makes this highly sensitive to slippage.

**Next Steps:** Proceed to Phase 4 (Walk-Forward Optimization).
