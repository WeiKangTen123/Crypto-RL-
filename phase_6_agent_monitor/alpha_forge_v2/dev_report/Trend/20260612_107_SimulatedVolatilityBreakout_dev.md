---
status: REJECTED
id: 107
class: SimulatedVolatilityBreakoutStrategy
coin: BTC
timeframe: 1h
sharpe: 0.00
return: 0.00
MDD: 0.00
win_rate: 0.00
trades: 0
PF: 0.00
date: 20260612
recommendation: REJECT
---

# Dev Report: SimulatedVolatilityBreakoutStrategy (ID 107)

**Alpha Hypothesis:** Exploits high-volatility breakouts after periods of low-volatility, identified via Z-score of price.
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 107

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.00 |
| Total Return | 0.00% |
| Max Drawdown | 0.00% |
| Win Rate | 0.00% |
| Total Trades | 0 |
| Profit Factor | 0.00 |
| Period | 2023-05-31 → 2026-05-31 |

---

## 2. Developer Recommendation

**Verdict: REJECT**

> The baseline backtest yielded zero trades over a 3-year period. This indicates that the Z-score threshold (3.0) and entry filters are far too restrictive for the 1H timeframe on BTC. The strategy is currently "dead" and requires broadening the parameter space or removing redundant filters to achieve execution.
