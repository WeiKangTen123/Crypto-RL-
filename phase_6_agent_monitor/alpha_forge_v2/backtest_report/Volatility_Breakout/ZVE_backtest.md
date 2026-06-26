# Backtest Report: Zero-Lag Volatility Expansion (ZVE)

**Date:** 2026-06-24
**Strategy ID:** 156
**Class:** ZVEStrategy (BTC 1H)
**Status:** MEDIOCRE (Optuna Tuned)

## 1. Final Optuna Parameters
- `kc_mult`: 2.2159 
- `chop_thresh`: 57.0941
- `tp_multiplier`: 3.1322
- `sl_multiplier`: 1.2735

## 2. Quantitative Results (2023 - 2026)
- **Total Return:** 38.4%
- **Sharpe Ratio:** 0.63
- **Total Trades:** 355

## 3. Analysis & Verdict
The strategy successfully cleared the >350 trade floor by lowering its filter requirements. However, it failed to break the 1.0 Sharpe threshold constraint. While profitable, the Zero-Lag MACD does not possess the same noise-canceling properties as direct order-flow (Taker Intensity), making it susceptible to lower quality breakouts. 

**Next Steps:** Held in backlog. Strategy 155 is superior.
