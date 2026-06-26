---
status: BAD
id: 113
class: InstitutionalMomentumConsolidationBreakoutStrategy
coin: BTC
timeframe: 1h
sharpe: 0.67
return: 194.2
MDD: 65.3
win_rate: 0.0
trades: 19
PF: 0.0
date: 20260618
recommendation: REJECT
---

# Dev Report: InstitutionalMomentumConsolidationBreakoutStrategy (ID 113)

**Alpha Hypothesis:** Institutional Momentum Consolidation Breakout
**Strategy Type:** Volatility Breakout
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 113

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.67 |
| Total Return | 194.2% |
| Max Drawdown | 65.3% |
| Win Rate | 0.0% |
| Total Trades | 19 |
| Profit Factor | 0.0 |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | 0.67 | ❌ Primary — failed |

---

## 3. Developer Recommendation

**Verdict: REJECT**

> Despite a positive total return (likely from one massive open trade held to the end), the strategy has 0 closed winning trades out of 19 attempts, resulting in a Profit Factor of 0.0. The Max Drawdown is also critically high at 65.3%. The consolidation breakout logic requires tighter risk controls and better take-profit triggers to realize gains.
