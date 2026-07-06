---
status: BAD
id: 116
sharpe: 0.04
return: -0.9
MDD: 19.8
win_rate: 8.3
trades: 72
PF: 1.14
date: 20260618
recommendation: REJECT
---

# Dev Report: ETHMomentumSqueezeStrategy (ID 116)

**Alpha Hypothesis:** ETH Momentum Bollinger Keltner Squeeze
**Strategy Type:** Volatility Breakout
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 116

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.04 |
| Total Return | -0.9% |
| Max Drawdown | 19.8% |
| Win Rate | 8.3% |
| Total Trades | 72 |
| Profit Factor | 1.14 |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | ETH / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 1h | 0.04 | ❌ Primary — failed |

---

## 3. Developer Recommendation

**Verdict: REJECT**

> The Bollinger Band / Keltner Channel squeeze logic correctly identifies contraction periods, but the breakout confirmation lacks directional accuracy (Win rate: 8.3%). It gets caught in "fakeouts" and gets stopped out immediately. However, the profit factor is > 1.0 (1.14), which means when it *does* catch a runner, the wins are massive. It needs a much better entry confirmation filter (like Volume Profile or Order Flow delta) to improve the win rate before it can be profitable.
