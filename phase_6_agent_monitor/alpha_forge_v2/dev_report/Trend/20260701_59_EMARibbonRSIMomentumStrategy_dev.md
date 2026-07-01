# Development Report — EMA Ribbon RSI Momentum
**Date:** 2026-07-01 | **ID:** 59 | **Class:** EMARibbonRSIMomentumStrategy | **Coin:** BTC | **TF:** 1H

---

## Stage Summary

| Stage | Status | Notes |
|---|---|---|
| 1/8 INGEST | ✓ | `calc_ema_ribbon`, `calc_rsi`, `calc_atr` verified in library.py |
| 2/8 BUILD | ✓ | Triple EMA alignment + crossover trigger + RSI gate |
| 3/8 SYNTAX | ✓ | AST clean |
| 4/8 SMOKE | ✓ | Bug fixed: `row.get('ema_f', 0)` / `row.get('ema_m', 0)` → direct access |
| 5/8 DEV_REPORT | ✓ | Baseline backtest completed |
| 6/8 WFO_EVO | PENDING | |
| 7/8 PBO_AUDIT | PENDING | |
| 8/8 MANIFEST | PENDING | |

---

## Baseline Backtest Results
**Period:** 2021-01-01 → 2026-05-31 | **Leverage:** 10× | **Risk/Trade:** 10%

| Metric | Value |
|---|---|
| Total Return | +34.56% |
| Annual Return | +5.64% |
| Sharpe Ratio | 0.41 |
| Max Drawdown | 20.06% |
| Total Trades | 119 |
| Grade | **MEDIOCRE** |

**Grade Reason:** Sharpe 0.41 below GOOD threshold. Low MDD (20.1%) is encouraging — the strategy is cautious. 119 trades = ~22/year, appropriate frequency for 1H.

---

## Trade Character
- 119 trades over 5.5 years, ~22/year — consistent low-frequency
- Max drawdown 20% is the best of the three new strategies
- EMA 55 lag means entries are typically 1-3 days into a trend — safe but late
- Crossover trigger (`require_crossover=True`) is working correctly — no over-trading

## Expert Commentary

The EMA Ribbon approach is one of the most battle-tested trend structures. The low MDD (20%) vs TII (27%) and BBW (45%) confirms the ribbon's regime-filtering value. The gap between total return (+35%) and Sharpe (0.41) suggests inconsistency across years — likely strong in 2023-2024 bull but flat in 2022 chop.

**Most promising of the three for finetune** — clean structure, low drawdown, only needs Sharpe improvement.

## Next Steps
1. Finetune EMA periods (try 8/18/50, 12/26/60) and RSI threshold
2. Test on ETH 4H — likely better performance in trending regimes
3. Consider adding ATR expansion filter (only trade when volatility is expanding)

---
*Hypothesis:* `hypho_report/Trend_Momentum/20260701_59_EMARibbonRSIMomentumStrategy_hypho.md`
