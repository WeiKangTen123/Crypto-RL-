---
status: IMPLEMENTED
id: 93
class: MultiTFRSIMACDDivergenceStrategy
coin: BNB
timeframe: 1h
sharpe: 1.57
return: 83.4
MDD: 9.6
win_rate: 36.8
trades: 38
PF: 2.69
date: 20260612
recommendation: PASS
---

# Dev Report: MultiTFRSIMACDDivergenceStrategy (ID 93)

**Alpha Hypothesis:** RSI + MACD divergence across multiple timeframes
**Strategy Type:** Multi-TF Divergence
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 93

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.57 |
| Total Return | 83.4% |
| Max Drawdown | 9.6% |
| Win Rate | 36.8% |
| Total Trades | 38 |
| Profit Factor | 2.69 |
| Avg Hold Duration | — |
| Period | 2023-01-01 → 2026-05-01 |
| Coin / Timeframe | BNB / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BNB / 1h | 1.57 | ✅ Primary — confirmed |
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
| 1 | 2023-02-15 | 🟢 LONG | $304.05 | $327.36 | +$76.12 | Signal triggered — TP exit |
| 2 | 2023-02-16 | 🟢 LONG | $324.76 | $322.14 | -$9.22 | Signal triggered — SL exit |
| 3 | 2023-07-08 | 🔴 SHORT | $235.18 | $240.92 | -$26.55 | Signal triggered — SL exit |
| 4 | 2023-08-03 | 🔴 SHORT | $239.68 | $243.92 | -$18.91 | Signal triggered — SL exit |
| 5 | 2023-08-10 | 🔴 SHORT | $242.08 | $223.50 | +$77.75 | Signal triggered — TP exit |

---

## 4. Regime Behaviour

**Optimal Regime:** RSI + MACD divergence across multiple timeframes
**Regime Label:** Any

The equity curve reflects performance across BTC/ETH market cycles from 2023-01-01 to 2026-05-01, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Low trade count (38) — insufficient for robust statistical validation
- Multi-TF divergence requires all signals aligned — many potential entries are filtered
- Late entries on confirmed divergence — much of the move may already be complete

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.57 meets the GOOD threshold. Trade count of 38 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 93` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
