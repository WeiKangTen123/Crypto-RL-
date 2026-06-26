---
status: MEDIOCRE
id: 119
sharpe: 1.04
return: 178.0
MDD: 23.0
win_rate: 44.8
trades: 98
PF: 1.71
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_ETH_RSI_TREND_STABLE (ID 119)

**Alpha Hypothesis:** RSI trend signal with ATR expansion and EMA trend triple-filter
**Strategy Type:** Momentum + Multi-Filter Conservative
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 119

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.04 |
| Total Return | 178.0% |
| Max Drawdown | 23.0% |
| Win Rate | 44.8% |
| Total Trades | 98 |
| Profit Factor | 1.71 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.04 | ✅ Primary |
| BTC / 4h | 1.09 | ✅ Better on BTC |
| ETH / 1h | 0.82 | ⚠️ Borderline |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> The MDD of 23% is the standout feature — lowest in the V2 batch. All 5 years are profitable. However the absolute ROI (178%) is below portfolio targets, and the Sharpe of 1.04 barely clears the acceptable threshold.
>
> Cross-asset test shows BTC/4h performs *better* (1.09 Sharpe) than ETH/4h — this is unusual and suggests the signal is driven more by macro trend strength than ETH-specific behavior. Consider reregistering on BTC/4h as the primary instrument.
>
> **Best as a portfolio diversifier or "always-on" conservative allocation. Lower returns but lowest risk of margin call at 10x.**
