---
status: IMPLEMENTED
id: 96
class: DonchianBreakoutStrategy
coin: BTC
timeframe: 4h
sharpe: 1.42
return: 96.2
MDD: 9.2
win_rate: 30.3
trades: 33
PF: 2.96
date: 20260612
recommendation: PASS
---

# Dev Report: DonchianBreakoutStrategy (ID 96)

**Alpha Hypothesis:** Donchian channel breakout with volume expansion
**Strategy Type:** Breakout / Trend-Following
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 96

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.42 |
| Total Return | 96.2% |
| Max Drawdown | 9.2% |
| Win Rate | 30.3% |
| Total Trades | 33 |
| Profit Factor | 2.96 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.42 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation is pending for this backfill report. Run `strategy-tuner` cross-asset check to complete section 2.

---

## 3. Trade Character

**Long/Short Split:** Data from primary backtest period.
**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-01-10 | 🟢 LONG | $17,441.57 | $17,339.85 | -$6.33 | Signal triggered — SL exit |
| 2 | 2023-01-11 | 🟢 LONG | $17,559.07 | $18,820.83 | +$70.84 | Signal triggered — TP exit |
| 3 | 2023-01-12 | 🟢 LONG | $18,894.79 | $21,372.19 | +$138.84 | Signal triggered — TP exit |
| 4 | 2023-01-20 | 🟢 LONG | $22,678.54 | $22,339.26 | -$18.57 | Signal triggered — SL exit |
| 5 | 2023-01-29 | 🟢 LONG | $23,909.79 | $23,653.55 | -$13.26 | Signal triggered — SL exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Donchian channel breakout with volume expansion
**Regime Label:** Trending

The equity curve reflects performance across BTC/ETH market cycles from 2021-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Low trade count (33) — borderline for statistical significance
- Donchian breakouts in choppy markets generate false signals
- No regime filter — can trade during low-ADX consolidation periods

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.42 meets the GOOD threshold. Trade count of 33 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 96` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
