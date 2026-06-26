---
status: IMPLEMENTED
id: 140
class: ChoppinessGatedSupertrendStrategy
coin: BTC
timeframe: 4h
sharpe: 0.69
return: 21.9
MDD: 11.5
win_rate: 37.5
trades: 8
PF: 2.85
date: 20260623
recommendation: REJECT
---

# Dev Report: ChoppinessGatedSupertrendStrategy (ID 140)

**Alpha Hypothesis:** Supertrend breakout gated by Choppiness index and ADX for high-quality trend continuation.
**Built by:** @alpha-developer
**Date:** 2026-06-23
**Registered:** `settings.py` ID 140

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.69 |
| Total Return | 21.9% |
| Max Drawdown | 11.5% |
| Win Rate | 37.5% |
| Total Trades | 8 |
| Profit Factor | 2.85 |

---

## 2. Developer Recommendation

**Verdict: REJECT**

> Generated automatically after Optuna finetuning. Only 8 trades — hard minimum not met (pure luck, nothing to tune).
