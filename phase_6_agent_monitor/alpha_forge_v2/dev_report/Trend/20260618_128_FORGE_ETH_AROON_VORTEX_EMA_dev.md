---
status: BAD
id: 128
sharpe: 0.78
return: 163.0
MDD: 37.0
win_rate: 33.8
trades: 94
PF: 1.38
date: 20260618
recommendation: REJECT
---

# Dev Report: FORGE_ETH_AROON_VORTEX_EMA (ID 128)

**Alpha Hypothesis:** Aroon crossover + Vortex trend filter + EMA trend long with tight ATR exit (new indicator test)
**Strategy Type:** Multi-Indicator Trend Confirmation — Vortex Validation
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 128

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.78 |
| Total Return | 163.0% |
| Max Drawdown | 37.0% |
| Win Rate | 33.8% |
| Total Trades | 94 |
| Profit Factor | 1.38 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 0.78 | ❌ Primary — below threshold |
| BTC / 4h | 0.71 | ❌ Weak |

---

## 3. Developer Recommendation

**Verdict: REJECT**

> The Vortex Indicator validation test results are instructive but the strategy as composed is not viable. Triple confirmation (Aroon + Vortex + EMA) creates excessive lag — all three indicators confirm trend inception *after* the fact, missing early entries and often entering at trend exhaustion points. The 2022 loss (-28%) is the critical failure.
>
> **Key finding on Vortex Indicator:** The VI+/VI- crossover is a valid trend confirmation signal, but its lag characteristics make it unsuitable as a standalone filter. It works better combined with a *leading* signal (like FVG or CVD delta) rather than *lagging* signals (like Aroon and EMA). Recommend testing Vortex as a filter on top of #125 (FVG + taker) in a future search run.
>
> Profit Factor 1.38 and 33.8% win rate are below minimum acceptable thresholds. 94 trades over 4 years (~23/year) is too few for statistical significance at this Sharpe.
>
> **REJECT — Vortex as filter on lagging signals fails. Vortex itself may have merit with leading entry signals. Archive to autopsy_report for reference.**
