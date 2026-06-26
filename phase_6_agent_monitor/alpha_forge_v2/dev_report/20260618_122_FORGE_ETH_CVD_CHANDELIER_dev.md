---
status: MEDIOCRE
id: 122
sharpe: 1.22
return: 221.0
MDD: 31.4
win_rate: 39.8
trades: 134
PF: 1.67
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_ETH_CVD_CHANDELIER (ID 122)

**Alpha Hypothesis:** Cumulative Volume Delta crossover with Chandelier trailing exit
**Strategy Type:** Order Flow + Adaptive Trailing Stop
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 122

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.22 |
| Total Return | 221.0% |
| Max Drawdown | 31.4% |
| Win Rate | 39.8% |
| Total Trades | 134 |
| Profit Factor | 1.67 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.22 | ✅ Primary |
| BTC / 4h | 1.14 | ✅ Cross-asset |
| ETH / 1h | 1.01 | ✅ Works on shorter TF |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> CVD is a leading indicator — the delta of taker buys vs sells shifts before price, giving genuine predictive value. The 2022 positive year (+19%) demonstrates that CVD correctly identified accumulation even during the macro bear.
>
> The ETH/1h showing Sharpe 1.01 (unlike most strategies which degrade on 1h) suggests CVD retains its edge at shorter timeframes — worth investigating as a multi-timeframe system.
>
> **Main gap: no secondary filter on the CVD entry. Adding taker confirm or WR filter would likely push Sharpe to 1.4+. Good candidate for further development. REVIEW pending signal enhancement.**
