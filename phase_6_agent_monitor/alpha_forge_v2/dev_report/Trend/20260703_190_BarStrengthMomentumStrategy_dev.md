# Dev Report — BarStrengthMomentumStrategy (ID 190)

**Date:** 2026-07-03  
**Source:** `report/101 Formulaic Alphas.pdf` — Alpha#53 (Kakushadze, WorldQuant 2015)  
**Factor Card:** `factor_library/Trend_Momentum/20260703_bar_strength_momentum.md`  
**Strategy File:** `strategy_backtest/strategies/bar_strength_momentum_strategy.py`  
**Grade:** BAD

---

## Alpha#53 Original Formula
```
-delta( ((close-low) - (high-close)) / (close-low), 9 )
```
Simplified: rate-of-change of a Williams %R-like bar position metric, negated (contrarian).

## Adaptation for Crypto
Simplified denominator from `(close-low)` to `(high-low)` for stability:
```
bar_strength = (2*close - high - low) / (high - low)   # -1 to +1
bs_delta     = bar_strength - bar_strength.shift(bs_period)
```
Direction changed to **momentum** (not contrarian): long when bs_delta > threshold.
ADX gate added to ensure directional market.

## Architecture
- `bar_strength = (2*close - high - low) / (high-low).clip(1e-8)`
- `bs_delta = bar_strength - bar_strength.shift(bs_period)`
- Long: `bs_delta > threshold AND ADX > adx_threshold`
- Short: `bs_delta < -threshold AND ADX > adx_threshold`
- Exit: ATR trailing stop (3×) + initial SL (2×)

## Backtest Results (BTC/4H, 2021-01-01 → 2026-05-31)

| Metric | Value |
|--------|-------|
| Sharpe | -2.67 |
| ROI | -99.47% |
| MDD | 99.59% |
| Win Rate | 30.69% |
| Trades | 795 |
| Profit Factor | 0.73 |

## Root Cause: Over-Trading
- `bs_period=9` delta of 0.3 on 4H bars is too easily achieved
- ADX(14) > 25 filters only ~40% of bars — insufficient gate
- 795 trades / 5.5yr on 4H ≈ 144/yr ≈ 2.8/week → still fee-heavy

## Recommended Fix for Finetune
- Raise `entry_threshold` to 0.5–0.7 (bar must fully switch character within 9 bars)
- Raise `adx_threshold` to 30–40
- Try longer `bs_period` (15–20) to require sustained bar-strength shift
