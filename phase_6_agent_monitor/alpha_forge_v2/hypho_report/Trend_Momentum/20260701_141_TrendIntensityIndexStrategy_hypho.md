# Hypothesis Report — Trend Intensity Index (TII)
**Date:** 2026-07-01 | **Strategy ID:** 141 | **Class:** TrendIntensityIndexStrategy

---

## Alpha Hypothesis

**Core Idea:** The TII measures the *percentage of positive deviations* from a long-period SMA over a minor window. When most of the recent closes are above the SMA (TII > 80), the market is in a confirmed, high-intensity uptrend. The strategy trades the momentum of that consensus rather than the crossover itself.

**Mathematical Formulation:**
```
SMA_major    = SMA(Close, major_period=60)
Positive_dev = max(Close - SMA_major, 0) for each bar in minor window (30 bars)
Negative_dev = max(SMA_major - Close, 0)

TII = 100 × Σ(Positive_dev) / (Σ(Positive_dev) + Σ(Negative_dev))
```

- `TII > 80` → 80%+ of the minor window closes are above the SMA → bullish trend intensity
- `TII < 20` → 80%+ of closes are below SMA → bearish trend intensity
- `TII = 50` → equal distribution → no trend

**Entry Logic:**
- Long: TII crosses above `tii_upper` (80) AND Close > SMA-200
- Short: TII crosses below `tii_lower` (20) AND Close < SMA-200

**Exit Logic:**
- Fixed R/R: TP at `tp_atr_mult × ATR`, SL at `sl_atr_mult × ATR`
- Signal exit: TII crosses back through 50

---

## Source & Provenance
- **Paper / Reference:** M.H. Pee, *"Trend Intensity Index"*, TradingPedia
- **Originality:** Classic indicator adapted for crypto 4H regime

## Expected Edge
TII avoids the noise of standard RSI (which measures rate of change) by measuring *consensus* — how consistently price stays above its mean. This creates fewer but higher-confidence signals, particularly suited to BTC 4H trending regimes.

## Hypothesised Regime
- **Best:** Strong trend (Bull or Bear) — 2020-2021, 2023 recovery, 2024-2025 bull
- **Worst:** Choppy/range-bound — BBW squeeze periods

## Risk Flags
- Highly regime-sensitive — lagged entry on strong trends
- SMA-200 filter adds safety but reduces trade count significantly

---
*Factor Card:* `factor_library/Trend_Momentum/20260527_trend_intensity_index_tii.md`
