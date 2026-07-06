---
status: IMPLEMENTED
id: 35
class: VWAPATRReversionStrategy
coin: BNB
timeframe: 4h
sharpe: 1.34
return: 167.2
MDD: 19.8
win_rate: 2.0
trades: 99
PF: 23.49
date: 20260612
recommendation: PASS
---

# Dev Report: VWAPATRReversionStrategy (ID 35)

**Alpha Hypothesis:** VWAP deviation with ATR-confirmed reversion
**Strategy Type:** Mean Reversion / VWAP
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 35

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.34 |
| Total Return | 167.2% |
| Max Drawdown | 19.8% |
| Win Rate | 2.0% |
| Total Trades | 99 |
| Profit Factor | 23.49 |
| Avg Hold Duration | — |
| Period | 2020-01-01 → 2026-05-31 |
| Coin / Timeframe | BNB / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BNB / 4h | 1.34 | ✅ Primary — confirmed |
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
| 1 | 2022-12-31 | 🔴 SHORT | $246.78 | $246.90 | -$1.0 | Signal triggered — SL exit |
| 2 | 2022-12-31 | 🟢 LONG | $246.42 | $246.30 | -$1.0 | Signal triggered — SL exit |
| 3 | 2023-01-01 | 🟢 LONG | $245.42 | $245.30 | -$1.0 | Signal triggered — SL exit |
| 4 | 2023-01-01 | 🟢 LONG | $244.12 | $244.00 | -$1.0 | Signal triggered — SL exit |
| 5 | 2023-01-01 | 🟢 LONG | $244.52 | $244.40 | -$0.99 | Signal triggered — SL exit |

---

## 4. Regime Behaviour

**Optimal Regime:** VWAP deviation with ATR-confirmed reversion
**Regime Label:** Ranging

The equity curve reflects performance across BTC/ETH market cycles from 2020-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Win rate of only 2% on primary — highly dependent on few large winners
- VWAP reset logic can cause signal gaps at daily/weekly boundaries
- ATR-based entries can miss fast reversions that complete within 1 bar

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.34 meets the GOOD threshold. Trade count of 99 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 35` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
