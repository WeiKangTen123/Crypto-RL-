---
status: IMPLEMENTED
id: 141
class: AVSStrategy
coin: BTC
timeframe: 4h
sharpe: 0.96
return: 21.4
MDD: 5.3
win_rate: 36.4
trades: 11
PF: 3.45
date: 20260623
recommendation: REJECT
---

# Dev Report: AVSStrategy (ID 141)

**Alpha Hypothesis:** Adaptive Volatility Squeeze (AVS) strategy triggering on combined BB/KC squeeze and Fisher transform momentum.
**Built by:** @alpha-developer
**Date:** 2026-06-23
**Registered:** `settings.py` ID 141

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.96 |
| Total Return | 21.4% |
| Max Drawdown | 5.3% |
| Win Rate | 36.4% |
| Total Trades | 11 |
| Profit Factor | 3.45 |

---

## 2. Developer Recommendation

**Verdict: REJECT**

> Generated automatically after Optuna finetuning. Only 11 trades — below CLT minimum of 30; metrics statistically unreliable.
