---
status: IMPLEMENTED
id: 139
class: KalmanFilteredMomentumStrategy
coin: BTC
timeframe: 4h
sharpe: -1.07
return: -79.0
MDD: 82.0
win_rate: 34.8
trades: 322
PF: 0.78
date: 20260623
recommendation: REJECT
---

# Dev Report: KalmanFilteredMomentumStrategy (ID 139)

**Alpha Hypothesis:** Momentum strategy gated by Kalman Filter smoothing and Chandelier ATR exits.
**Built by:** @alpha-developer
**Date:** 2026-06-23
**Registered:** `settings.py` ID 139

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | -1.07 |
| Total Return | -79.0% |
| Max Drawdown | 82.0% |
| Win Rate | 34.8% |
| Total Trades | 322 |
| Profit Factor | 0.78 |

---

## 2. Developer Recommendation

**Verdict: REJECT**

> Generated automatically after Optuna finetuning. Sharpe -1.07 < 0.3 — no meaningful edge.
