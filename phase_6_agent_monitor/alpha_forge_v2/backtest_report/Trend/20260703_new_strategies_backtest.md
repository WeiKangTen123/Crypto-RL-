# Backtest Report — New Strategies (2026-07-03)
**Scanned:** 3 strategies | **Period:** 2021-01-01 → 2026-05-31 | **Leverage:** 10× | **No finetune**

---

## Results Summary

| ID | Strategy | Class | Coin | TF | Return | Sharpe | MDD | WR | Trades | Grade |
|---|---|---|---|---|---|---|---|---|---|---|
| 183 | Supertrend Pro Volatility | SupertrendProVolatilityStrategy | BTC | 4H | -8.94% | 0.09 | 67.27% | 41.58% | 190 | BAD |
| 184 | Diamond Triangle Breakout | DiamondTriangleBreakoutStrategy | BTC | 4H | +2.14% | 0.10 | 21.68% | 29.89% | 87 | BAD |
| 185 | RSI Divergence Mean Reversion | RsiDivergenceMeanReversionStrategy | BTC | 4H | -30.65% | -1.25 | 31.33% | 22.58% | 31 | BAD |

---

## Analysis

### ID 183 — Supertrend Pro Volatility (BAD)
Relative volume + RSI zone filter on Supertrend flip. Default multiplier (3.0) causes whipsaws — 2023 lost 43.6%. MDD 67% is critical.
**Finetune potential:** High — widen st_multiplier → should tighten entry count and improve quality.

### ID 184 — Diamond Triangle Breakout (BAD but closest to viable)
BB squeeze → volume-confirmed breakout → ADX filter. Positive total return (+2.14%) and 5/6 years showed small gains. PF 1.04, WR 30% — barely break-even.
**Finetune potential:** Medium — tighter squeeze_pct and higher vol_spike_mult may improve WR significantly.

### ID 185 — RSI Divergence Mean Reversion (BAD, likely structural)
Only 31 trades over 5.5yr with 22.6% WR, negative all years. BTC 4H trends too strongly for this divergence style.
**Recommendation:** Try 1H BTC or ETH before finetuning — low signal count suggests parameter mismatch not strategy flaw.

---

## Factor Cards Updated
- `factor_library/Trend_Momentum/20260526_supertrend_pro_volatility.md` → COMPLETED (built, backtested, BAD)
- `factor_library/Volatility_Breakout/20260526_diamond_triangle_breakout.md` → COMPLETED (built, backtested, BAD)
- `factor_library/Mean_Reversion/20260526_rsi_divergence_mean_reversion.md` → COMPLETED (built, backtested, BAD)

---

*Dev Reports:*
- `dev_report/Trend/20260703_183_SupertrendProVolatilityStrategy_dev.md`
- `dev_report/Volatility_Breakout/20260703_184_DiamondTriangleBreakoutStrategy_dev.md`
- `dev_report/Trend/20260703_185_RsiDivergenceMeanReversionStrategy_dev.md`
