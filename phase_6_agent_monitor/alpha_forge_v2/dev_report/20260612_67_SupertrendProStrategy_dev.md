---
status: IMPLEMENTED
id: 67
class: SupertrendProStrategy
coin: ETH
timeframe: 4h
sharpe: 1.23
return: 183.6
MDD: 33.5
win_rate: 45.8
trades: 59
PF: 1.83
date: 20260612
recommendation: PASS
---

# Dev Report: SupertrendProStrategy (ID 67)

**Alpha Hypothesis:** Supertrend directional flip with ATR volatility confirmation
**Strategy Type:** Trend-Following / Volatility
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 67

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.23 |
| Total Return | 183.6% |
| Max Drawdown | 33.5% |
| Win Rate | 45.8% |
| Total Trades | 59 |
| Profit Factor | 1.83 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.23 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation pending. Run `strategy-tuner` cross-asset check to complete.

---

## 3. Trade Character

**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-01-04 | 🟢 LONG | $1,251.37 | $1,510.67 | +$206.62 | Signal triggered — EXIT exit |
| 2 | 2023-01-24 | 🔴 SHORT | $1,555.19 | $1,612.75 | -$45.26 | Signal triggered — EXIT exit |
| 3 | 2023-03-03 | 🔴 SHORT | $1,564.66 | $1,459.04 | +$77.78 | Signal triggered — EXIT exit |
| 4 | 2023-03-23 | 🟢 LONG | $1,837.91 | $1,716.12 | -$82.58 | Signal triggered — EXIT exit |
| 5 | 2023-04-10 | 🟢 LONG | $1,889.67 | $1,861.86 | -$17.56 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Supertrend directional flip with ATR volatility confirmation
**Regime Label:** Trending

Performance spans 2021-01-01 → 2026-05-31, covering bull, bear, and ranging BTC/ETH cycles. Full regime breakdown available via Phase 4 dashboard equity curve.

---

## 5. Known Weaknesses

- XRP/4h configuration — different liquidity/microstructure than BTC
- Supertrend can whipsaw in ranging XRP markets causing rapid position flips
- Cross-asset validation needed — XRP regulatory risk adds tail risk

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.23 meets the GOOD threshold. Trade count of 59 is on the lower side — Optuna fine-tuning should focus on improving signal frequency alongside quality.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 67` to find optimal parameters.
