---
status: BAD
id: 114
class: ZScoreStatArbStrategy
coin: BTC
timeframe: 1h
sharpe: 0.04
return: 0.1
MDD: 1.4
win_rate: 50.0
trades: 2
PF: 2.09
date: 20260618
recommendation: REJECT
---

# Dev Report: ZScoreStatArbStrategy (ID 114)

**Alpha Hypothesis:** Z-Score Statistical Arbitrage
**Strategy Type:** Mean Reversion
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 114

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.04 |
| Total Return | 0.1% |
| Max Drawdown | 1.4% |
| Win Rate | 50.0% |
| Total Trades | 2 |
| Profit Factor | 2.09 |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | 0.04 | ❌ Primary — failed |

---

## 3. Developer Recommendation

**Verdict: REJECT**

> The strategy only executed 2 trades across 5 years of data. The combination of Z-Score > 3.0 and requiring a strict candlestick pattern confirmation filters out almost all opportunities. It needs optimization (lowering thresholds) to achieve statistical significance.
