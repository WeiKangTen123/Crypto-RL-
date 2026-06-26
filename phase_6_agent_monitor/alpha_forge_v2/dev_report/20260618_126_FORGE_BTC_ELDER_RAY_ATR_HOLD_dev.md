---
status: MEDIOCRE
id: 126
sharpe: 1.03
return: 255.0
MDD: 42.0
win_rate: 40.1
trades: 148
PF: 1.52
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_BTC_ELDER_RAY_ATR_HOLD (ID 126)

**Alpha Hypothesis:** Elder Ray on BTC with ATR expansion filter and max hold exit
**Strategy Type:** Trend Momentum — BTC Specialist
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 126

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.03 |
| Total Return | 255.0% |
| Max Drawdown | 42.0% |
| Win Rate | 40.1% |
| Total Trades | 148 |
| Profit Factor | 1.52 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.03 | ⚠️ Primary — borderline |
| ETH / 4h | 0.88 | ❌ Weaker on ETH |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> Elder Ray on BTC benefits from BTC's longer, more sustained trend legs compared to ETH. The ATR expansion filter improves signal quality vs unfiltered #123. Max hold exit is the appropriate exit for BTC's slow-turning trends.
>
> However, MDD of 42% is too high for comfortable 10x leverage deployment — BTC's 2022 drawdown (-65% spot) heavily impacts this strategy. The strategy needs a bear-regime filter (funding rate, put/call ratio, or 200W MA reference) to suppress entries during macro downtrends.
>
> **ETH (0.88 Sharpe) is not a viable secondary asset for this configuration. BTC-specific strategy. REVIEW — needs regime filter before paper trading.**
