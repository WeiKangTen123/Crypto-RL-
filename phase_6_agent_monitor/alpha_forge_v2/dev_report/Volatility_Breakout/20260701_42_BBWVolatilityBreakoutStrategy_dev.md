# Development Report — BBW Volatility Breakout
**Date:** 2026-07-01 | **ID:** 42 | **Class:** BBWVolatilityBreakoutStrategy | **Coin:** BTC | **TF:** 1H

---

## Stage Summary

| Stage | Status | Notes |
|---|---|---|
| 1/8 INGEST | ✓ | `calc_bbw` verified in library.py |
| 2/8 BUILD | ✓ | Strategy class with squeeze detection + volume filter |
| 3/8 SYNTAX | ✓ | AST clean |
| 4/8 SMOKE | ✓ | Bug fixed: `row.get('BBM', 0)` → `row['BBM']` |
| 5/8 DEV_REPORT | ✓ | Baseline backtest completed |
| 6/8 WFO_EVO | PENDING | |
| 7/8 PBO_AUDIT | PENDING | |
| 8/8 MANIFEST | PENDING | |

---

## Baseline Backtest Results
**Period:** 2021-01-01 → 2026-05-31 | **Leverage:** 10× | **Risk/Trade:** 10%

| Metric | Value |
|---|---|
| Total Return | +9.59% |
| Annual Return | +1.71% |
| Sharpe Ratio | 0.19 |
| Max Drawdown | 45.24% |
| Total Trades | 480 |
| Grade | **BAD** |

**Grade Reason:** Sharpe 0.19 below MEDIOCRE threshold. 480 trades on 1H is over-trading — false breakouts dominate. High MDD (45.2%) confirms the strategy is taking many small wins and large losses.

---

## Trade Character
- 480 trades over 5.5 years = ~87 trades/year (over-trading for 1H)
- Volume filter helps but is insufficient on 1H BTC (too much noise)
- The `EXIT` on BB Middle cross creates very short trades — many stopped before full move develops

## Expert Commentary

The BBW squeeze is a valid concept but the 1H timeframe on BTC is too noisy. The squeeze resolves into false breakouts more than 60% of the time. Recommended next steps:
1. Move to 4H or daily timeframe
2. Tighten squeeze definition (lower percentile threshold)
3. Add ADX filter (only trade when ADX > 20 at breakout)

---

## Next Steps
- Finetune on 4H BTC/SOL with tighter squeeze detection
- Consider marking as REJECTED on 1H if finetune doesn't reach Sharpe > 0.5

---
*Hypothesis:* `hypho_report/Volatility_Breakout/20260701_42_BBWVolatilityBreakoutStrategy_hypho.md`
