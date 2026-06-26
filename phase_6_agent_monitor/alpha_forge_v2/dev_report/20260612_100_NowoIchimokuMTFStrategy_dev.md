---
status: IMPLEMENTED
id: 100
class: NowoIchimokuMTFStrategy
coin: BTC
timeframe: 4h
sharpe: 1.24
return: 242.8
MDD: 25.4
win_rate: 32.8
trades: 58
PF: 2.01
date: 20260612
recommendation: PASS
---

# Dev Report: NowoIchimokuMTFStrategy (ID 100)

**Alpha Hypothesis:** Ichimoku cloud structure with multi-TF alignment
**Strategy Type:** Multi-TF Trend
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 100

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.24 |
| Total Return | 242.8% |
| Max Drawdown | 25.4% |
| Win Rate | 32.8% |
| Total Trades | 58 |
| Profit Factor | 2.01 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.24 | ✅ Primary — confirmed |
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
| 1 | 2023-02-15 | 🟢 LONG | $23,330.56 | $23,170.68 | -$7.35 | Signal triggered — EXIT exit |
| 2 | 2023-03-03 | 🔴 SHORT | $22,331.75 | $23,209.30 | -$39.5 | Signal triggered — SL exit |
| 3 | 2023-03-13 | 🟢 LONG | $23,993.71 | $28,782.70 | +$189.47 | Signal triggered — EXIT exit |
| 4 | 2023-04-27 | 🟢 LONG | $29,164.30 | $28,509.60 | -$26.18 | Signal triggered — EXIT exit |
| 5 | 2023-05-03 | 🟢 LONG | $29,040.67 | $28,851.76 | -$7.8 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Ichimoku cloud structure with multi-TF alignment
**Regime Label:** Trending

The equity curve reflects performance across BTC/ETH market cycles from 2021-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- ETH-specific Ichimoku config — cross-asset validity needs verification
- Cloud calculations require 52-bar warm-up before first signal
- Strategy may overtrade in ranging ETH markets without trend confirmation

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.24 meets the GOOD threshold. Trade count of 58 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 100` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
