---
status: MEDIOCRE
id: 118
sharpe: 1.18
return: 190.0
MDD: 32.0
win_rate: 38.2
trades: 143
PF: 1.62
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_ETH_BB_BREAKOUT_EMA_ATR (ID 118)

**Alpha Hypothesis:** Bollinger Band breakout in macro EMA uptrend with ATR exits
**Strategy Type:** Volatility Breakout + Trend Filter
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 118

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.18 |
| Total Return | 190.0% |
| Max Drawdown | 32.0% |
| Win Rate | 38.2% |
| Total Trades | 143 |
| Profit Factor | 1.62 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.18 | ✅ Primary |
| BTC / 4h | 0.94 | ⚠️ Marginal |
| ETH / 1h | 0.71 | ❌ Not viable |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> The BB breakout + EMA macro filter is a sound concept but 2022 shows the weakness: upper band breaks during sustained downtrends generate expensive false signals. The EMA filter helps but the long-period EMA lags the trend shift by weeks.
>
> Cross-asset results are mixed — BTC/4h is marginal at 0.94 Sharpe. The strategy is ETH-specific in its current parameter configuration.
>
> **Requires regime filter (e.g., rolling volatility percentile or crypto fear index) before paper trading. Held for further tuning.**
