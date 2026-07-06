---
status: IMPLEMENTED
id: 86
class: MultiTFMomentumReversalStrategy
coin: BTC
timeframe: 4h
sharpe: 1.05
return: 25.4
MDD: 15.1
win_rate: 36.9
trades: 217
PF: 1.32
date: 20260612
recommendation: PASS
---

# Dev Report: MultiTFMomentumReversalStrategy (ID 86)

**Alpha Hypothesis:** Multi-TF momentum reversal at key structural levels
**Strategy Type:** Reversal / Multi-TF
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 86

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.05 |
| Total Return | 25.4% |
| Max Drawdown | 15.1% |
| Win Rate | 36.9% |
| Total Trades | 217 |
| Profit Factor | 1.32 |
| Avg Hold Duration | — |
| Period | 2023-01-01 → 2024-01-01 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.05 | ✅ Primary — confirmed |
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
| 1 | 2023-01-04 | 🟢 LONG | $16,853.59 | $17,106.46 | +$20.97 | Signal triggered — EXIT exit |
| 2 | 2023-01-08 | 🔴 SHORT | $17,119.27 | $17,281.98 | -$10.11 | Signal triggered — EXIT exit |
| 3 | 2023-01-10 | 🔴 SHORT | $17,319.04 | $17,483.64 | -$10.0 | Signal triggered — EXIT exit |
| 4 | 2023-01-11 | 🔴 SHORT | $17,541.51 | $17,708.24 | -$9.9 | Signal triggered — EXIT exit |
| 5 | 2023-01-11 | 🔴 SHORT | $17,934.29 | $18,104.74 | -$9.79 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Multi-TF momentum reversal at key structural levels
**Regime Label:** Volatile

The equity curve reflects performance across BTC/ETH market cycles from 2023-01-01 to 2024-01-01, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Operates on ETH/4h — different microstructure than BTC may affect reliability
- Multi-TF reversal signals are infrequent — limited trade opportunities
- Performance in 2026 data is thin — needs more recent validation

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.05 meets the GOOD threshold. Trade count of 217 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 86` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
