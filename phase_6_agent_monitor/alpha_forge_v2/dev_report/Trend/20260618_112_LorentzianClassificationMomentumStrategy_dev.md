---
status: BAD
id: 112
class: LorentzianClassificationMomentumStrategy
coin: BTC
timeframe: 1h
sharpe: -21.92
return: -100.0
MDD: 100.0
win_rate: 19.6
trades: 4219
PF: 0.25
date: 20260618
recommendation: REJECT
---

# Dev Report: LorentzianClassificationMomentumStrategy (ID 112)

**Alpha Hypothesis:** Lorentzian Classification Momentum
**Strategy Type:** Machine Learning / KNN Pattern Matcher
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 112

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | -21.92 |
| Total Return | -100.0% |
| Max Drawdown | 100.0% |
| Win Rate | 19.6% |
| Total Trades | 4219 |
| Profit Factor | 0.25 |
| Period | 2023-05-31 → 2026-05-31 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | -21.92 | ❌ Primary — failed |

---

## 3. Developer Recommendation

**Verdict: REJECT**

> The strategy severely overtrades (4219 trades in 3 years) due to noisy KNN classifications on the 1h timeframe. The friction (fees + slippage) combined with 10x leverage completely destroys the account, resulting in a -100% return and a catastrophic -21.92 Sharpe. Needs structural logic changes (e.g., higher confidence threshold or moving to 4h/1d) before it can be considered viable.
