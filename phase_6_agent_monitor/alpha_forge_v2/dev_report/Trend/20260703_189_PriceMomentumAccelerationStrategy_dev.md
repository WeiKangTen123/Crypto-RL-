# Dev Report — PriceMomentumAccelerationStrategy (ID 189)

**Date:** 2026-07-03  
**Source:** `report/101 Formulaic Alphas.pdf` — Alpha#46 (Kakushadze, WorldQuant 2015)  
**Factor Card:** `factor_library/Trend_Momentum/20260703_price_momentum_acceleration.md`  
**Strategy File:** `strategy_backtest/strategies/price_momentum_acceleration_strategy.py`  
**Grade:** BAD

---

## Alpha#46 Original Formula
```
v = (delay(close,20) - delay(close,10))/10 - (delay(close,10) - close)/10
     = (close + delay(close,20) - 2*delay(close,10)) / 10

if v > 0.25: signal = -1
elif v < 0:  signal = +1
else:        signal = -sign(delta(close, 1))
```

## Adaptation for Crypto
The original uses a fixed threshold (0.25) and assumes equity cross-sectional context.
For single-asset crypto:
1. Normalise `v` as `accel_pct = v_raw / close` (% terms)
2. Apply rolling z-score over `zscore_period` bars for dynamic thresholding
3. Entry when |z| > `entry_threshold` (contrarian: fade extreme momentum acceleration)

## Architecture
- `accel_pct = (close + close.shift(slow) - 2*close.shift(fast)) / close`
- `accel_z = calc_zscore(accel_pct, zscore_period)` from library
- Long: `accel_z < -threshold` | Short: `accel_z > +threshold`
- Exit: ATR trailing stop (3×) + initial SL (2×)

## Backtest Results (ETH/1H, 2021-01-01 → 2026-05-31)

| Metric | Value |
|--------|-------|
| Sharpe | -4.05 |
| ROI | -100% |
| MDD | 100% |
| Win Rate | 30.27% |
| Trades | 2038 |
| Profit Factor | 0.59 |

## Root Cause: Over-Trading
- `zscore_period=100` + `entry_threshold=1.5` fires on ~14% of bars (by z-score definition)
- On ETH/1H with 47411 bars: ~6600 potential signals → 2038 actual trades after alternation
- Fee drag: 0.05% × 2 × 2038 ≈ 2038% cumulative fee load → account ruined rapidly

## Recommended Fix for Finetune
- Raise `entry_threshold` to 2.0–2.5 (reduces signal frequency to 2-5%)
- Extend `fast_period` and `slow_period` to smooth acceleration
- Test on 4H instead of 1H to reduce frequency
