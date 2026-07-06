# Backtest Report — BarStrengthMomentumStrategy (ID 190)

**Grade:** MEDIOCRE  
**Date:** 2026-07-03  
**Asset:** BTC/4H | Period: 2021-01-01 → 2026-05-31  
**Source:** 101 Formulaic Alphas — Alpha#53 (Kakushadze, WorldQuant 2015)

## Results (Post-Finetune)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 0.44 |
| Sortino Ratio | 0.66 |
| Calmar Ratio | 0.25 |
| Total Return | +65.15% |
| Max Drawdown | 39.03% |
| Profit Factor | 1.04 |
| Win Rate | 31.50% |
| Total Trades | 327 |

## Yearly Returns

| Year | Return |
|------|--------|
| 2021 | +32.32% |
| 2022 | +16.42% |
| 2023 | +12.90% |
| 2024 | +18.88% |
| 2025 | -17.86% |
| 2026 | -2.76% |

## Key Params
- bs_period=11, entry_threshold=0.27, adx_period=13, adx_threshold=32.4
- atr_trail_mult=5.0× (boundary ceiling hit — wider trail likely better)

## Notes
4 of 6 years positive. Strong 2022 bear year (+16%).
Boundary: atr_period at floor (7), atr_trail_mult at ceiling (5.0).
ADX gate tightening from 25→32 was the critical fix.
