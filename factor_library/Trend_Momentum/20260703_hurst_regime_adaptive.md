---
name: hurst-regime-adaptive
strategy_id: 193
type: adaptive
factor_class: Trend_Momentum
directional_bias: Symmetric
optimal_regime: Any (self-selecting)
timeframes: 4h, 1h
coins: ETH, BTC
source: Fujimoto et al. (2025) "Enhanced scaling crossover detection in long-range correlated time series" — Chaos, Solitons & Fractals: X 14 (2025) 100125
interest: High
status: COMPLETED
sharpe: 0.80
win_rate: 36.76
total_return: 166.63
max_drawdown: 39.31
tags: [built, backtested, finetuned, hurst, variance-ratio, regime-adaptive, DFA, MEDIOCRE]
---
# Hurst Regime Adaptive Strategy

## Concept
Inspired by DFA (Detrended Fluctuation Analysis) research on long-range correlations and
scaling crossovers in financial time series. Uses the **Variance Ratio** (Lo-MacKinlay 1988)
as a fast proxy for the Hurst exponent to detect market regime:

```
VR(k) = Var(k-bar returns) / (k × Var(1-bar returns))

VR > 1.0:  persistent process  → H > 0.5 → TRENDING regime  → momentum signal
VR < 1.0:  anti-persistent     → H < 0.5 → REVERTING regime → mean-reversion signal
VR ≈ 1.0:  random walk         → H ≈ 0.5 → NEUTRAL          → stay flat
```

## Signal Logic

**Trending (VR > 1 + vr_band):**
- Long: close breaks above N-bar rolling high (momentum breakout)
- Short: close breaks below N-bar rolling low

**Reverting (VR < 1 - vr_band):**
- Long: z-score of close < −threshold (oversold)
- Short: z-score of close > +threshold (overbought)

**Neutral (|VR − 1| < vr_band):** signal = 0 (flat)

## Exit Logic
- ATR trailing stop ratchet (initial SL + ratcheting trail)

## Performance (ETH/4H, 2021-2026, post-finetune)
| Metric | Value |
|--------|-------|
| Sharpe | 0.80 |
| ROI | +166.63% |
| MDD | 39.31% |
| Trades | 68 |
| Win Rate | 36.76% |
| Profit Factor | 1.65 |

### Yearly Returns
| Year | Return |
|------|--------|
| 2021 | +10.35% |
| 2022 | -11.92% |
| 2023 | +17.07% |
| 2024 | +35.92% |
| 2025 | +29.06% |
| 2026 | +33.58% |

### Key Finetune Changes
- vr_band: 0.15 → 0.38 (neutral zone tripled; ~60% of bars now flat)
- mom_period: 14 → 26 (longer breakout avoids noise)
- rev_threshold: 1.5 → 2.58σ (only enter MR at extreme readings)
- Result: Sharpe improved from -1.30 → +0.80 (best in Alpha-series library)

## Connections
**Category:** [[Trend_Momentum/_Index]]
**Source Paper:** `report/1-s2.0-S2590054424000228-main.pdf`
**Related:** [[Mean_Reversion/20260526_hmm_regime_classifier]] · [[Trend_Momentum/20260703_intrabar_efficiency_momentum]]
