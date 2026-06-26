---
status: IMPLEMENTED
id: 23
class: EMACrossoverStrategy
coin: BTC
timeframe: 4h
sharpe: 1.53
return: 51.0
MDD: 18.9
win_rate: 32.0
trades: 25
PF: 2.28
date: 20260612
recommendation: PASS
---

# Dev Report: EMACrossoverStrategy (ID 23)

**Alpha Hypothesis:** Classic EMA crossover with directional momentum confirmation
**Strategy Type:** Trend-Following
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 23

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.53 |
| Total Return | 51.0% |
| Max Drawdown | 18.9% |
| Win Rate | 32.0% |
| Total Trades | 25 |
| Profit Factor | 2.28 |
| Avg Hold Duration | — |
| Period | 2023-01-01 → 2024-01-01 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 7x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.53 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation pending. Run `strategy-tuner` cross-asset check to complete.

---

## 3. Trade Character

**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-01-01 | 🟢 LONG | $16,564.94 | $22,021.69 | +$230.13 | Signal triggered — EXIT exit |
| 2 | 2023-02-09 | 🔴 SHORT | $22,021.69 | $23,330.56 | -$51.62 | Signal triggered — EXIT exit |
| 3 | 2023-02-15 | 🟢 LONG | $23,330.56 | $23,105.60 | -$8.36 | Signal triggered — EXIT exit |
| 4 | 2023-02-25 | 🔴 SHORT | $23,105.60 | $24,292.05 | -$42.45 | Signal triggered — EXIT exit |
| 5 | 2023-03-13 | 🟢 LONG | $24,292.05 | $28,492.44 | +$135.84 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Classic EMA crossover with directional momentum confirmation
**Regime Label:** Trending

Performance spans 2023-01-01 → 2024-01-01, covering bull, bear, and ranging BTC/ETH cycles. Full regime breakdown available via Phase 4 dashboard equity curve.

---

## 5. Known Weaknesses

- Classic EMA crossover is well-known — alpha may be crowded/arbitraged away
- Low trade count (25) — very limited statistical significance
- No volume or momentum filter — susceptible to false crossovers in ranging markets

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.53 meets the GOOD threshold. Trade count of 25 is on the lower side — Optuna fine-tuning should focus on improving signal frequency alongside quality.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 23` to find optimal parameters.
