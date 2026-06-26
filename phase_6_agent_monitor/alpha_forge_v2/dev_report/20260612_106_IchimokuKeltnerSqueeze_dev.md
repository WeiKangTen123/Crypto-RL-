---
status: REJECTED
id: 106
class: IchimokuKeltnerSqueezeStrategy
coin: BTC
timeframe: 1h
sharpe: -2.81
return: -29.95
MDD: 30.27
win_rate: 29.47
trades: 95
PF: 0.36
date: 20260612
recommendation: REJECT
---

# Dev Report: IchimokuKeltnerSqueezeStrategy (ID 106)

**Alpha Hypothesis:** Combines Ichimoku Cloud direction with Keltner Channel breakouts after a Bollinger Squeeze.
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 106

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | -2.81 |
| Total Return | -29.95% |
| Max Drawdown | 30.27% |
| Win Rate | 29.47% |
| Total Trades | 95 |
| Profit Factor | 0.36 |
| Period | 2023-01-01 → 2024-01-01 |

---

## 2. Developer Recommendation

**Verdict: REJECT**

> The baseline backtest shows extreme underperformance with a Sharpe Ratio of -2.81. The strategy's logic of requiring "No Squeeze" during a cloud cross appears to be counter-productive, leading to late entries and catching the tail end of moves. Significant structural refactoring is required before this can move to optimization.
