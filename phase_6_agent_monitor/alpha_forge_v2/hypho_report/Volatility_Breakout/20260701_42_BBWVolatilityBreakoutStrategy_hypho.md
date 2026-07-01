# Hypothesis Report — BBW Volatility Breakout
**Date:** 2026-07-01 | **Strategy ID:** 42 | **Class:** BBWVolatilityBreakoutStrategy

---

## Alpha Hypothesis

**Core Idea:** Bollinger Band Width (BBW) is a normalised measure of volatility. When BBW compresses below its own moving average, the market is in a squeeze — coiling energy before an expansion. The strategy enters the first bar that breaks outside the bands, capturing the initial impulse of the expansion.

**Mathematical Formulation:**
```
BB_Upper = SMA(Close, 20) + std(Close, 20) × 2
BB_Lower = SMA(Close, 20) - std(Close, 20) × 2
BB_Mid   = SMA(Close, 20)

BBW = (BB_Upper - BB_Lower) / BB_Mid

Squeeze = BBW < SMA(BBW, bbw_sma_period)   ← prior bar in squeeze
Long  = Close > BB_Upper AND prev_squeeze AND Volume > SMA(Volume, vol_sma_period)
Short = Close < BB_Lower AND prev_squeeze AND Volume > SMA(Volume, vol_sma_period)
```

**Entry Logic:**
- Squeeze detected on bar N (BBW < its SMA)
- On bar N+1: price breaks out of band + volume spike confirms

**Exit Logic:**
- Price crosses back through BB Middle Band → EXIT
- ATR trailing stop

---

## Source & Provenance
- **Source:** GitHub quantitative breakout strategies, standard volatility compression play
- **Originality:** Volume filter + squeeze-then-break timing is the key addition

## Expected Edge
Crypto exhibits strong volatility clustering. Extended squeeze periods (BBW at multi-month lows) are reliably followed by expansion. Volume confirmation filters false breakouts caused by thin liquidity.

## Hypothesised Regime
- **Best:** Post-consolidation breakouts (e.g., accumulation phases)
- **Worst:** High-volatility trending (already expanded BBW → no squeeze to trigger)

## Risk Flags
- False breakouts common in ranging market — volume filter is critical
- Short timeframes (15m/1h) generate many signals with low average quality

---
*Factor Card:* `factor_library/Volatility_Breakout/20260527_bbw_volatility_breakout.md`
