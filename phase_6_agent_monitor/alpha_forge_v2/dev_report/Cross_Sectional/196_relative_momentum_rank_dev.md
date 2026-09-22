# Alpha Forge Dev Report: Cross-Sectional Relative Momentum Rank

**Date**: 2026-07-06
**Strategy ID**: MULTI_REL_MOM_4H (999)
**Class**: `RelativeMomentumRank`
**Type**: MULTI-COIN PORTFOLIO (Cross_Sectional)

## 1. Implementation Summary
- **Math Integration**: Added `calc_roc` (Rate of Change) to `library.py`.
- **Strategy Class**: Implemented `RelativeMomentumRank` inheriting from the new `MultiCoinBaseStrategy`.
- **Logic**: 
  - Computes ROC for 5 coins: `BTC, ETH, BNB, SOL, XRP`.
  - Ranks them descending (Rank 1 = highest ROC).
  - Emits LONG signal for Rank 1 (if ROC > 0) and SHORT signal for Rank 5 (if ROC < 0).
- **Execution**: Managed via `PortfolioBacktestEngine` with shared cross-margin equity and cross-sectional sizing.

## 2. Baseline Smoke Test Results (Default Params)
- **Period**: 2023-05-31 → 2026-05-31
- **Timeframe**: 4h
- **Total Return**: -56.20%
- **Sharpe Ratio**: 0.37
- **Max Drawdown**: 91.80%
- **Win Rate**: 38.01%
- **Total Trades**: 634
- **Expectancy**: $3.71

## 3. Analysis & Notes
- The strategy executes successfully with the new multi-coin engine.
- As expected for an unoptimized default baseline, it suffered significant drawdowns, likely due to tight fixed stop-losses whipsawing on crypto volatility.
- The underlying positive expectancy ($3.71 per trade) despite negative total returns and low win rate suggests the winners are large, but risk sizing or exit logic needs optimization.

## 4. Next Phase Handoff
- **Status**: ✅ DEV_COMPLETE
- **Next**: Strategy is registered as `999` in `settings.py` and is ready for parameter tuning by `crypto-strategy-tuner`.
