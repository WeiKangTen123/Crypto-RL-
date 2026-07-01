# Hypothesis Report — Supertrend EMA Filter
**Date:** 2026-07-01 | **Strategy ID:** 182 | **Class:** SupertrendEmaFilterStrategy

---

## Alpha Hypothesis

**Core Idea:** The Supertrend indicator generates non-repainting trend flip signals. When price breaks above the upper band (bearish→bullish flip), it marks the moment the market has confirmed an uptrend. Filtering these flips with an EMA-200 macro regime guard eliminates signals that swim against the dominant trend — the worst losses in Supertrend come from catching flips during prolonged bear markets.

**Mathematical Formulation:**
```
ATR = ATR(st_period)
UpperBand = HL2 + st_multiplier × ATR   (sticky: only tightens)
LowerBand = HL2 - st_multiplier × ATR   (sticky: only tightens)
Supertrend direction: flips to +1 when Close breaks UpperBand,
                      flips to -1 when Close breaks LowerBand

Long  entry: st_dir[t] == +1  AND  st_dir[t-1] == -1   (flip to bullish)
             AND  Close > EMA(ema_period)   (macro uptrend)
Short entry: st_dir[t] == -1  AND  st_dir[t-1] == +1   (flip to bearish)
             AND  Close < EMA(ema_period)   (macro downtrend)

Exit:  SL = entry ± sl_atr_mult × ATR
       TP = entry ± SL_dist × tp_rr
       OR  Supertrend flips against position (signal exit)
```

**Candle direction for same-bar SL/TP:** When both SL and TP are hit on the same bar, bullish bar → SL fires first (price fell then recovered), bearish bar → TP fires first (price rose then fell).

---

## Source & Provenance
- **Source:** Web research — classic Supertrend + EMA macro filter combination
- **Originality:** Supertrend flip as a precise crossover trigger (not just direction) + EMA-200 regime guard

## Expected Edge
Supertrend flips are concentrated at trend inflection points. The EMA-200 filter eliminates fakeout flips that happen during consolidation within a larger bear trend. The combination should reduce false positives significantly vs. raw Supertrend.

## Hypothesised Regime
- **Best:** Strong directional trending markets (crypto bull cycle)
- **Worst:** Prolonged bear or sideways — many flips, all false

## Risk Flags
- Supertrend is inherently lagging — flip happens after breakout confirms
- In 2022 bear market, price oscillated around bands frequently → many whipsaws
- EMA-200 itself lags, so the filter may not engage fast enough in fast reversals

---
*Factor Card:* `factor_library/Trend_Momentum/20260527_supertrend_pro.md`
