---
status: GOOD
id: 120
sharpe: 1.49
return: 498.0
MDD: 36.8
win_rate: 43.1
trades: 162
PF: 1.94
date: 20260618
recommendation: PASS
---

# Dev Report: FORGE_ETH_EMA_SUPERTREND (ID 120)

**Alpha Hypothesis:** EMA crossover entry with Supertrend trailing stop exit
**Strategy Type:** Trend Momentum + Adaptive Trailing Stop
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 120

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.49 |
| Total Return | 498.0% |
| Max Drawdown | 36.8% |
| Win Rate | 43.1% |
| Total Trades | 162 |
| Profit Factor | 1.94 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.49 | ✅ Primary — strong |
| BTC / 4h | 1.31 | ✅ Cross-asset confirmed |
| SOL / 4h | 1.22 | ✅ Generalises to alts |

---

## 3. Developer Recommendation

**Verdict: PASS**

> Highest Sharpe (1.49) in the entire ForgeStrategy V2 batch at production risk. The Supertrend trailing stop is the key differentiator — it allows profitable trends to run far longer than any fixed TP would, then cuts losses when the trend genuinely reverses. The ATR basis of Supertrend ensures the stop adapts to the volatility regime.
>
> Excellent cross-asset generalization (BTC 1.31, SOL 1.22) confirms the signal is not ETH-specific curve-fitting. The EMA crossover entry is simple and robust.
>
> **One of the two highest-priority paper trading candidates (alongside #125). PASS.**
