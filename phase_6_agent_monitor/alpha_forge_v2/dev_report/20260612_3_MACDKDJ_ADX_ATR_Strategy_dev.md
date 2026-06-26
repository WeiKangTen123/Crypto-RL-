---
status: IMPLEMENTED
id: 3
class: MACDKDJ_ADX_ATR_Strategy
coin: BTC
timeframe: 4h
sharpe: 1.7
return: 2284.7
MDD: 50.7
win_rate: 52.1
trades: 48
PF: 3.97
date: 20260612
recommendation: PASS
---

# Dev Report: MACDKDJ_ADX_ATR_Strategy (ID 3)

**Alpha Hypothesis:** MACD + KDJ dual momentum with ADX trend strength filter
**Strategy Type:** Momentum / Multi-Indicator
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 3

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.7 |
| Total Return | 2284.7% |
| Max Drawdown | 50.7% |
| Win Rate | 52.1% |
| Total Trades | 48 |
| Profit Factor | 3.97 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 30x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.7 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation pending. Run `strategy-tuner` cross-asset check to complete.

---

## 3. Trade Character

**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-02-11 | 🟢 LONG | $21,873.48 | $21,772.65 | -$30.65 | Signal triggered — EXIT exit |
| 2 | 2023-02-13 | 🟢 LONG | $21,878.62 | $23,469.76 | +$418.56 | Signal triggered — TP exit |
| 3 | 2023-03-13 | 🟢 LONG | $22,469.95 | $26,235.90 | +$1384.91 | Signal triggered — TP exit |
| 4 | 2023-05-02 | 🟢 LONG | $28,554.95 | $28,880.67 | +$180.71 | Signal triggered — EXIT exit |
| 5 | 2023-05-31 | 🔴 SHORT | $27,154.32 | $26,907.93 | +$151.07 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** MACD + KDJ dual momentum with ADX trend strength filter
**Regime Label:** Trending

Performance spans 2021-01-01 → 2026-05-31, covering bull, bear, and ranging BTC/ETH cycles. Full regime breakdown available via Phase 4 dashboard equity curve.

---

## 5. Known Weaknesses

- High max drawdown (50.7%) — dangerous without strict position sizing
- Very low trade count (48) — thin statistical base
- ADX filter can suppress entries during early trend formation

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.7 meets the GOOD threshold. Trade count of 48 is on the lower side — Optuna fine-tuning should focus on improving signal frequency alongside quality.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 3` to find optimal parameters.
