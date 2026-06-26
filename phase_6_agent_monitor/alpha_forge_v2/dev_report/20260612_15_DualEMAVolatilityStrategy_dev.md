---
status: IMPLEMENTED
id: 15
class: DualEMAVolatilityStrategy
coin: ETH
timeframe: 4h
sharpe: 1.14
return: 56.9
MDD: 17.7
win_rate: 58.3
trades: 36
PF: 2.91
date: 20260612
recommendation: PASS
---

# Dev Report: DualEMAVolatilityStrategy (ID 15)

**Alpha Hypothesis:** Dual EMA crossover with volatility expansion gate
**Strategy Type:** Trend-Following / Volatility Filter
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 15

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.14 |
| Total Return | 56.9% |
| Max Drawdown | 17.7% |
| Win Rate | 58.3% |
| Total Trades | 36 |
| Profit Factor | 2.91 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.14 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation pending. Run `strategy-tuner` cross-asset check to complete.

---

## 3. Trade Character

**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-02-22 | 🟢 LONG | $1,614.54 | $1,615.29 | -$0.03 | Signal triggered — EXIT exit |
| 2 | 2023-03-03 | 🟢 LONG | $1,566.22 | $1,567.30 | +$0.18 | Signal triggered — EXIT exit |
| 3 | 2023-04-09 | 🟢 LONG | $1,837.96 | $1,857.99 | +$10.38 | Signal triggered — EXIT exit |
| 4 | 2023-05-18 | 🟢 LONG | $1,796.10 | $1,799.66 | +$1.5 | Signal triggered — EXIT exit |
| 5 | 2023-06-05 | 🟢 LONG | $1,821.51 | $1,805.59 | -$9.33 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Dual EMA crossover with volatility expansion gate
**Regime Label:** Trending

Performance spans 2021-01-01 → 2026-05-31, covering bull, bear, and ranging BTC/ETH cycles. Full regime breakdown available via Phase 4 dashboard equity curve.

---

## 5. Known Weaknesses

- EMA crossover is a lagging signal — entries after trend already established
- Volatility expansion gate may block valid entries during slow trend starts
- ETH/4h pair — needs verification that alpha holds on BTC primary pair

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.14 meets the GOOD threshold. Trade count of 36 is on the lower side — Optuna fine-tuning should focus on improving signal frequency alongside quality.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 15` to find optimal parameters.
