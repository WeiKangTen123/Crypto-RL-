---
status: MEDIOCRE
id: 124
sharpe: 1.19
return: 511.0
MDD: 43.0
win_rate: 38.5
trades: 221
PF: 1.58
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_ETH_HMA_TIGHT_ATR (ID 124)

**Alpha Hypothesis:** Hull Moving Average crossover (new indicator) with ATR expansion filter and tight ATR exit
**Strategy Type:** Low-Lag Trend Detection + Tight Exit
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 124

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.19 |
| Total Return | 511.0% |
| Max Drawdown | 43.0% |
| Win Rate | 38.5% |
| Total Trades | 221 |
| Profit Factor | 1.58 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.19 | ⚠️ Primary — MDD too high |
| BTC / 4h | 1.08 | ✅ Cross-asset holds |
| ETH / 1h | 0.84 | ⚠️ Degrades |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> **HMA validation confirmed** — the indicator generates genuinely earlier signals than standard EMA, contributing to high ROI (511%). However the MDD (43%) is the highest in the batch except for #126. The tight SL (2.68×ATR) gets triggered frequently in ETH's high-volatility bear market phases.
>
> Key finding: the HMA fast/slow periods (ema_fast=28, ema_slow=90) are optimised for 4h ETH trend momentum. These are not hyper-fitted — similar Sharpe appears on BTC/4h without re-optimisation.
>
> **Main issue: sl_atr_mult too tight for bear markets. Recommend re-running random search with sl_atr_mult range [3.0, 5.0] to find configurations with MDD < 35%. REVIEW pending re-run.**
