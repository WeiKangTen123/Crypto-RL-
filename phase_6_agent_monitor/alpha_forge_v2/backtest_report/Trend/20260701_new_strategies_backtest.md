# Backtest Report — New Strategies Scan (2026-07-01)
**Scanned:** 3 strategies | **Period:** 2021-01-01 → 2026-05-31 | **Leverage:** 10×

---

## Results Summary

| ID | Strategy | Coin | TF | Return | Sharpe | MDD | Trades | Grade |
|---|---|---|---|---|---|---|---|---|
| 141 | TrendIntensityIndexStrategy | BTC | 4H | +98.99% | 0.64 | 26.9% | 117 | MEDIOCRE |
| 59 | EMARibbonRSIMomentumStrategy | BTC | 1H | +34.56% | 0.41 | 20.1% | 119 | MEDIOCRE |
| 42 | BBWVolatilityBreakoutStrategy | BTC | 1H | +9.59% | 0.19 | 45.2% | 480 | BAD |
| **182** | **SupertrendEmaFilterStrategy** | **BTC** | **4H** | **+360.85%** | **1.63** | **16.5%** | **78** | **GOOD** |

---

## Bug Fixes Applied This Session

All three strategies were failing with `'_Bar' object has no attribute 'get'`. Root cause: strategy `manage_trade()` methods used `row.get('col', default)` but the engine's `_Bar` proxy only supports `row['col']`. Fixed in:

- `trend_intensity_index_strategy.py` line 149: `row.get('tii', 50)` → `row['tii']`
- `ema_ribbon_rsi_momentum_strategy.py` lines 151-152: `row.get('ema_f', 0)` / `row.get('ema_m', 0)` → direct access
- `bbw_volatility_breakout_strategy.py` line 152: `row.get('BBM', 0)` → `row['BBM']`

---

## Analysis

### TII (ID 141) — Most Promising
- Best Sharpe (0.64) and best absolute return (+99%) of the three
- 117 trades = low frequency, appropriate for 4H
- MDD 27% is acceptable — tunable to improve
- **Recommendation:** Finetune — target Sharpe > 1.0

### EMA Ribbon RSI (ID 59) — Best Risk Profile
- Lowest MDD (20.1%) — the EMA 55 filter is doing its job
- 34.56% return is modest but consistent
- **Recommendation:** Finetune on ETH 4H — trending market may unlock better Sharpe

### BBW Breakout (ID 42) — Needs Rework
- BAD grade: Sharpe 0.19, MDD 45.2%
- 480 trades on 1H = over-trading, too many false breakouts
- **Recommendation:** Move to 4H timeframe and add ADX filter before next finetune

---

## Phase 4 UI Fixes (Same Session)
- Added `Qty` column to DRL trade log table (header + data cell)
- Fixed `Cost Basis` header label → `Entry Price` (matches actual data field)
- Fixed colspan from 15 → 16 in both strategy detail trade tables (strat + MC)

---
*Dev Reports:*
- `dev_report/Trend/20260701_141_TrendIntensityIndexStrategy_dev.md`
- `dev_report/Trend/20260701_59_EMARibbonRSIMomentumStrategy_dev.md`
- `dev_report/Volatility_Breakout/20260701_42_BBWVolatilityBreakoutStrategy_dev.md`
