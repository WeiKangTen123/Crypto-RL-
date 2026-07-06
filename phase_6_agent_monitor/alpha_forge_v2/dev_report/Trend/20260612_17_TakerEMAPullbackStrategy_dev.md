---
status: IMPLEMENTED
id: 17
class: TakerEMAPullbackStrategy
coin: BTC
timeframe: 15m
sharpe: 1.15
return: 252.9
MDD: 24.8
win_rate: 56.5
trades: 271
PF: 1.49
date: 20260612
recommendation: PASS
---

# Dev Report: TakerEMAPullbackStrategy (ID 17)

**Alpha Hypothesis:** Taker buy pressure pullback to EMA mean
**Strategy Type:** Mean Reversion / Order Flow
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 17

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.15 |
| Total Return | 252.9% |
| Max Drawdown | 24.8% |
| Win Rate | 56.5% |
| Total Trades | 271 |
| Profit Factor | 1.49 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 15m |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 15m | 1.15 | ✅ Primary — confirmed |
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
| 1 | 2021-01-06 | 🟢 LONG | $34,602.21 | $38,864.86 | +$122.63 | Signal triggered — EXIT exit |
| 2 | 2021-01-13 | 🟢 LONG | $35,758.54 | $38,446.25 | +$83.74 | Signal triggered — EXIT exit |
| 3 | 2021-01-18 | 🟢 LONG | $36,908.44 | $35,257.87 | -$54.48 | Signal triggered — EXIT exit |
| 4 | 2021-02-02 | 🟢 LONG | $34,312.16 | $37,257.67 | +$98.12 | Signal triggered — EXIT exit |
| 5 | 2021-02-08 | 🟢 LONG | $40,391.18 | $45,833.56 | +$167.42 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Taker buy pressure pullback to EMA mean
**Regime Label:** Ranging

The equity curve reflects performance across BTC/ETH market cycles from 2021-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Taker buy pressure signal can be noisy during low-volume periods
- EMA pullback entries can be late — price may have already reversed
- Strategy is long-biased — underperforms in sustained bear markets

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.15 meets the GOOD threshold. Trade count of 271 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 17` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
