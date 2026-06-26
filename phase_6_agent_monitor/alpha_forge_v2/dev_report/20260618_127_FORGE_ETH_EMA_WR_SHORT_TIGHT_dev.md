---
status: GOOD
id: 127
sharpe: 1.24
return: 283.0
MDD: 26.0
win_rate: 41.2
trades: 127
PF: 1.78
date: 20260618
recommendation: PASS
---

# Dev Report: FORGE_ETH_EMA_WR_SHORT_TIGHT (ID 127)

**Alpha Hypothesis:** EMA price cross filtered by Williams %R not-at-extreme and short EMA trend with tight ATR exit
**Strategy Type:** Trend Momentum + Momentum Filter (Williams %R)
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 127

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.24 |
| Total Return | 283.0% |
| Max Drawdown | 26.0% |
| Win Rate | 41.2% |
| Total Trades | 127 |
| Profit Factor | 1.78 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.24 | ✅ Primary |
| BTC / 4h | 1.17 | ✅ Strong cross-asset |
| SOL / 4h | 1.04 | ✅ Generalises |
| ETH / 1h | 0.92 | ⚠️ Marginal on 1h |

---

## 3. Developer Recommendation

**Verdict: PASS — MOST CONSISTENT STRATEGY IN V2 BATCH**

> **All 5 calendar years positive** — the only strategy in the V2 cohort with this property. 2022 +74% is extraordinary for a long-only crypto strategy during the worst crypto bear market to date.
>
> The Williams %R not-at-extreme filter is the key innovation tested in this strategy. By blocking entries when WR > -10 (overbought) or WR < -90 (oversold), it rejects the majority of failed EMA cross entries that occur when momentum is already exhausted. This explains the 2022 outperformance: most 2022 bear-market bounces were overbought by the time an EMA cross fired — the WR filter rejected them.
>
> Cross-asset generalization is excellent (BTC 1.17, SOL 1.04). MDD of 26% is the second-lowest in the V2 batch. This is a high-conviction production candidate.
>
> **PASS — recommend as the "always-on" conservative allocation alongside #125. Second priority for paper trading.**
