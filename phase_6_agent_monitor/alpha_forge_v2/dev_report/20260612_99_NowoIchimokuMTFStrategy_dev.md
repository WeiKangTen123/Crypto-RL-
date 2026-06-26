---
status: IMPLEMENTED
id: 99
class: NowoIchimokuMTFStrategy
coin: BTC
timeframe: 1h
sharpe: 1.33
return: 316.3
MDD: 27.9
win_rate: 33.2
trades: 410
PF: 1.48
date: 20260612
recommendation: PASS
---

# Dev Report: NowoIchimokuMTFStrategy (ID 99)

**Alpha Hypothesis:** Multi-TF confluence — works best when 1h + 4h aligned
**Strategy Type:** Multi-Timeframe Momentum
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 99

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.33 |
| Total Return | 316.3% |
| Max Drawdown | 27.9% |
| Win Rate | 33.2% |
| Total Trades | 410 |
| Profit Factor | 1.48 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | 1.33 | ✅ Primary — confirmed |
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
| 1 | 2023-01-11 | 🟢 LONG | $17,417.09 | $21,032.21 | +$206.96 | Signal triggered — EXIT exit |
| 2 | 2023-01-20 | 🟢 LONG | $21,127.84 | $22,621.57 | +$84.65 | Signal triggered — EXIT exit |
| 3 | 2023-01-25 | 🟢 LONG | $23,604.35 | $23,027.13 | -$32.19 | Signal triggered — SL exit |
| 4 | 2023-01-25 | 🟢 LONG | $22,943.67 | $22,914.04 | -$2.25 | Signal triggered — EXIT exit |
| 5 | 2023-01-28 | 🟢 LONG | $23,103.79 | $22,967.15 | -$8.04 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Multi-TF confluence — works best when 1h + 4h aligned
**Regime Label:** Trending

The equity curve reflects performance across BTC/ETH market cycles from 2021-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Ichimoku requires long warm-up period — first 52 bars produce no signal
- Multi-TF alignment reduces trade frequency — may miss short-term opportunities
- Performance degrades when 1h and 4h timeframes are in disagreement

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.33 meets the GOOD threshold. Trade count of 410 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 99` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
