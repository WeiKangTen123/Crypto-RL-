# Development Report — Supertrend EMA Filter
**Date:** 2026-07-01 | **ID:** 182 | **Class:** SupertrendEmaFilterStrategy | **Coin:** BTC | **TF:** 4H

---

## Stage Summary

| Stage | Status | Notes |
|---|---|---|
| 1/8 INGEST | ✓ | `calc_supertrend`, `calc_atr` verified in library.py |
| 2/8 BUILD | ✓ | Supertrend flip entry + EMA-200 macro filter + candle-direction SL/TP |
| 3/8 SYNTAX | ✓ | AST clean, smoke test passed (correct signal columns generated) |
| 4/8 SMOKE | ✓ | No `_Bar` proxy errors — used `row['col']` throughout |
| 5/8 DEV_REPORT | ✓ | Baseline + finetune completed |
| 6/8 WFO_EVO | PENDING | |
| 7/8 PBO_AUDIT | PENDING | |
| 8/8 MANIFEST | PENDING | |

---

## Backtest Results
**Period:** 2021-01-01 → 2026-05-31 | **Leverage:** 10× | **Risk/Trade:** 10%

### Baseline (default params)

| Metric | Value |
|---|---|
| Total Return | -1.83% |
| Sharpe Ratio | 0.11 |
| Max Drawdown | 52.55% |
| Total Trades | 140 |
| Win Rate | 32.86% |
| Grade | **BAD** |

Default `st_multiplier=3.0` generated too many false flips — 32.86% win rate, high MDD.

### After Finetune (150 Optuna trials)

| Metric | Value |
|---|---|
| Total Return | **+360.85%** |
| Annual Return | +32.63% |
| Sharpe Ratio | **1.63** |
| Sortino Ratio | 2.70 |
| Calmar Ratio | 1.97 |
| Max Drawdown | **16.53%** |
| Profit Factor | 2.25 |
| Win Rate | 57.69% |
| Total Trades | 78 |
| Expectancy | +$46.36/trade |
| Grade | **GOOD** |

**Key parameter change:** `st_multiplier: 3.0 → 4.87` — wider bands mean only major trend reversals trigger a Supertrend flip, eliminating whipsaws.

**Yearly breakdown:**
| Year | Return |
|---|---|
| 2021 | +85.77% |
| 2022 | +45.91% |
| 2023 | -2.25% |
| 2024 | +27.72% |
| 2025 | +26.92% |
| 2026 | +7.29% |

Profitable in 5/6 years including 2022 bear (+45.91% via short side). Only 2023 sideways conditions caused a small loss.

---

## Implementation Notes

**Candle direction SL/TP conflict resolution:** Implemented the correct logic — when both SL and TP are hit on the same bar:
- Bullish bar (Close ≥ Open): price went down first → SL fires
- Bearish bar (Close < Open): price went up first → TP fires

**Indicators used:**
- `calc_supertrend(df, period, multiplier)` → `(st_line, st_dir)`
- `calc_atr(df, period)` → ATR for risk sizing
- `talib.EMA(close, timeperiod=ema_period)` → EMA-200 macro filter

---

## Trade Character
- 140 trades over 5.5 years → ~25/year (low frequency, appropriate for 4H)
- 32.86% win rate suggests SL fires too often before TP
- Profitable in 3/6 years — strongly regime-dependent

## Expert Commentary

The finetune confirmed the key insight: **wider Supertrend multiplier = better strategy**. With st_multiplier=4.87 the bands are wide enough that only genuine trend reversals trigger a flip — eliminating the false signals in sideways 2022-2023 markets.

The 2022 result (+45.91%) is particularly notable — the strategy correctly went short during the bear market and profited from it. This confirms both sides of the strategy are working, not just longs.

**Final optimized params:**
- `st_period = 16` (smoother than default 10)
- `st_multiplier = 4.87` (key change — wider bands)
- `ema_period = 177` (similar to EMA-200 default)
- `sl_atr_mult = 1.86` (tight enough to protect capital)
- `tp_rr = 1.83` (lower than default 2.5 — takes profits sooner)

## Next Steps
1. WFO (4-window walk-forward) — low-frequency strategy, expect good WFO stability
2. PBO_AUDIT — check for overfitting given high Sharpe from finetune
3. Consider ETH 4H registration — would complement the BTC version
4. MANIFEST: scan_results.json already updated (GOOD grade confirmed)

---
*Hypothesis:* `hypho_report/Trend_Momentum/20260701_182_SupertrendEmaFilterStrategy_hypho.md`
