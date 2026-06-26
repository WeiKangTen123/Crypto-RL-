---
status: IMPLEMENTED
id: 18
class: MACDKDJStrategy
coin: BNB
timeframe: 4h
sharpe: 1.27
return: 71.7
MDD: 13.6
win_rate: 42.5
trades: 40
PF: 2.78
date: 20260612
recommendation: PASS
---

# Dev Report: MACDKDJStrategy (ID 18)

**Alpha Hypothesis:** MACD + KDJ dual-signal momentum confirmation
**Strategy Type:** Momentum
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 18

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.27 |
| Total Return | 71.7% |
| Max Drawdown | 13.6% |
| Win Rate | 42.5% |
| Total Trades | 40 |
| Profit Factor | 2.78 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BNB / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BNB / 4h | 1.27 | ✅ Primary — confirmed |
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
| 1 | 2023-02-27 | 🟢 LONG | $308.25 | $302.95 | -$17.7 | Signal triggered — EXIT exit |
| 2 | 2023-03-13 | 🟢 LONG | $304.95 | $309.65 | +$14.61 | Signal triggered — EXIT exit |
| 3 | 2023-04-05 | 🟢 LONG | $314.76 | $311.64 | -$10.34 | Signal triggered — EXIT exit |
| 4 | 2023-04-30 | 🟢 LONG | $337.67 | $328.34 | -$27.71 | Signal triggered — EXIT exit |
| 5 | 2023-05-05 | 🟢 LONG | $325.66 | $320.24 | -$16.4 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** MACD + KDJ dual-signal momentum confirmation
**Regime Label:** Trending

The equity curve reflects performance across BTC/ETH market cycles from 2021-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Low trade count (40) limits statistical confidence
- MACD + KDJ dual confirmation reduces entry frequency significantly
- KDJ is sensitive to its lookback period — small changes alter signals substantially

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.27 meets the GOOD threshold. Trade count of 40 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 18` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
