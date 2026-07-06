# Backtest Report — PriceMomentumAccelerationStrategy (ID 189)

**Grade:** MEDIOCRE  
**Date:** 2026-07-03  
**Asset:** ETH/1H | Period: 2021-01-01 → 2026-05-31  
**Source:** 101 Formulaic Alphas — Alpha#46 (Kakushadze, WorldQuant 2015)

## Results (Post-Finetune)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 0.75 |
| Sortino Ratio | 1.10 |
| Calmar Ratio | 0.72 |
| Total Return | +232.96% |
| Max Drawdown | 34.38% |
| Profit Factor | 1.30 |
| Win Rate | 38.32% |
| Total Trades | 214 |

## Yearly Returns ★ All 6 Years Positive ★

| Year | Return |
|------|--------|
| 2021 | +31.86% |
| 2022 | +28.44% |
| 2023 | +27.10% |
| 2024 | +12.79% |
| 2025 | +15.58% |
| 2026 | +18.65% |

## Key Params
- fast_period=5, slow_period=39, zscore_period=150
- entry_threshold=2.79σ (key fix: was 1.5, fires too often)
- atr_trail_mult=5.07× (wide trail, lets mean-reversion play out)

## Notes
Only strategy in library with ALL years positive across 2021-2026.
Boundary warnings: fast_period at floor (5), atr_trail_mult at ceiling (5.07).
Second pass with fast_period in (2,5) and trail in (5,8) may push toward GOOD.
