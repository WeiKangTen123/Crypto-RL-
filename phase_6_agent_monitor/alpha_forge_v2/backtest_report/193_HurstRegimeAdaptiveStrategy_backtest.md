# Backtest Report — HurstRegimeAdaptiveStrategy (ID 193)

**Grade:** MEDIOCRE  
**Date:** 2026-07-03  
**Asset:** ETH/4H | Period: 2021-01-01 → 2026-05-31  
**Source:** Fujimoto et al. (2025) — Chaos, Solitons & Fractals: X 14 (2025) 100125

## Results (Post-Finetune)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 0.80 |
| Sortino Ratio | 1.19 |
| Calmar Ratio | 0.51 |
| Total Return | +166.63% |
| Max Drawdown | 39.31% |
| Profit Factor | 1.65 |
| Win Rate | 36.76% |
| Total Trades | 68 |
| Expectancy | $25.38 / trade |

## Yearly Returns

| Year | Return |
|------|--------|
| 2021 | +10.35% |
| 2022 | -11.92% |
| 2023 | +17.07% |
| 2024 | +35.92% |
| 2025 | +29.06% |
| 2026 | +33.58% |

## Key Params (Post-Finetune)
- vr_window=167, vr_k=11, vr_band=0.3781 (only fires when VR >1.38 or <0.62)
- mom_period=26 (26-bar high/low breakout in trending regime)
- rev_zscore_period=19, rev_threshold=2.58 (only enter MR at 2.58σ extremes)
- atr_trail_mult=4.08× (wide trail lets trades breathe)

## Regime Interpretation
- **Trending** (VR > 1.38): Market shows persistence. Enter breakouts of 26-bar range.
- **Reverting** (VR < 0.62): Market shows anti-persistence. Fade 2.58σ extremes.
- **Neutral** (|VR − 1| < 0.38): Market is near random walk. Stay flat.

## Notable Strengths
- **Sharpe 0.80** — highest in the Alpha-series library (189-193)
- **Profit Factor 1.65** — strongest edge-per-trade ratio in the series
- **5/6 years positive** — only 2022 slightly negative (-12% vs ETH -68% that year)
- **Expectancy $25.38/trade** — high absolute value per entry
- **Wide vr_band** means fewer but higher-quality entries

## Why It Works
The variance ratio detects whether recent returns show persistence (trending) or
anti-persistence (mean-reverting). A wide threshold (0.38) ensures we only enter in
STRONG regime conditions. By being flat in random-walk conditions (~60% of the time),
the strategy avoids the noise that destroys most level-signal approaches.

2022: Lost -11.92% despite ETH crashing 68% — the reverting-mode MR trades were
correctly catching oversold bounces, partially offsetting bear losses.

## Notes
Boundary: atr_period hit floor (7). Trades are 68 — below GOOD threshold of 100.
The selectivity is the source of edge, but also limits annual compounding.
A second pass with wider OPTIMIZATION_RANGES on vr_window may find a peak that
achieves both Sharpe ≥ 1.0 AND ≥ 100 trades.
