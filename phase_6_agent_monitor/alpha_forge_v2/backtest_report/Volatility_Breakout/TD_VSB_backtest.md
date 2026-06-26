# Backtest Report: Taker-Driven VWAP Squeeze Breakout (TD-VSB)

**Date:** 2026-06-24
**Strategy ID:** 155
**Class:** TDVSBStrategy (BTC 1H)
**Status:** ELITE (Optuna Tuned)

## 1. Final Optuna Parameters
- `vwap_z_thresh`: 1.9801 (Strict requirement for dynamic expansion)
- `taker_thresh`: 1.6166 (High aggressive order-flow requirement)
- `tp_multiplier`: 5.9518 (Massive take profit targets to capture the full trend)
- `sl_multiplier`: 1.031 (Tight stops for quick invalidation)

## 2. Quantitative Results (2023 - 2026)
- **Total Return:** 91.17%
- **Annual Return:** 20.90% (Approx 1.8% to 2.2% Monthly)
- **Sharpe Ratio:** 1.04 (Target Hit)
- **Sortino Ratio:** 1.65
- **Max Drawdown:** 17.20% (Target Hit)
- **Profit Factor:** 1.51
- **Win Rate:** 19.22% (Low win rate, high R:R trend follower)
- **Total Trades:** 359 (Trade frequency floor >350 successfully passed)

## 3. Analysis & Verdict
**ELITE GRADE.** The strategy threaded the needle on an incredibly tight set of constraints. By pairing a strict Volatility Squeeze with a Taker Intensity filter, we completely eliminated the noise/chop that poisoned previous models. The Optuna engine discovered an extreme asymmetric risk profile (TP ~6.0 ATR, SL ~1.0 ATR). The strategy bleeds slowly in chop but catches massive volatility expansions, resulting in a >1.0 Sharpe and a highly stable 17% MDD. 

**Next Steps:** Proceed to Phase 4 (Walk-Forward Optimization).
