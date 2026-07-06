---
status: MEDIOCRE
id: 121
sharpe: 1.31
return: 245.0
MDD: 28.5
win_rate: 37.4
trades: 198
PF: 1.55
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_ETH_BB_ATR_CLEAN (ID 121)

**Alpha Hypothesis:** Unfiltered Bollinger Band breakout with ATR exits
**Strategy Type:** Volatility Breakout (Minimal Filter)
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 121

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.31 |
| Total Return | 245.0% |
| Max Drawdown | 28.5% |
| Win Rate | 37.4% |
| Total Trades | 198 |
| Profit Factor | 1.55 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.31 | ✅ Primary |
| BTC / 4h | 1.08 | ✅ Cross-asset |
| ETH / 1h | 0.74 | ❌ Too noisy |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> The minimal BB breakout has respectable Sharpe (1.31) but the unfiltered approach increases trade count (198) and generates more churn. 2022 loss (-8%) reflects the lack of trend direction confirmation. Profit Factor 1.55 is marginal.
>
> This is the "stress test" version — comparing against #118 (same entry + EMA filter) shows the filter adds 0.13 Sharpe but reduces trade count. The tradeoff depends on portfolio capacity.
>
> **Viable as a high-frequency breakout component. Needs monitoring period before paper trading. REVIEW.**
