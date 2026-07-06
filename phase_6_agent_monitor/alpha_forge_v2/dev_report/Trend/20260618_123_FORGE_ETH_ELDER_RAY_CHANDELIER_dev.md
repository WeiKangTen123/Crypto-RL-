---
status: MEDIOCRE
id: 123
sharpe: 1.00
return: 168.0
MDD: 29.8
win_rate: 36.9
trades: 176
PF: 1.48
date: 20260618
recommendation: REVIEW
---

# Dev Report: FORGE_ETH_ELDER_RAY_CHANDELIER (ID 123)

**Alpha Hypothesis:** Elder Ray Bull Power entry with Chandelier trailing exit
**Strategy Type:** Momentum Oscillator + Trailing Stop
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 123

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.00 |
| Total Return | 168.0% |
| Max Drawdown | 29.8% |
| Win Rate | 36.9% |
| Total Trades | 176 |
| Profit Factor | 1.48 |
| Period | 2022-01-01 → 2026-06-18 |
| Coin / Timeframe | ETH / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| ETH / 4h | 1.00 | ⚠️ Primary — borderline |
| BTC / 4h | 0.91 | ⚠️ Weak |
| ETH / 1h | 0.62 | ❌ Fails |

---

## 3. Developer Recommendation

**Verdict: REVIEW**

> Elder Ray (Bull Power = High - EMA) fires frequently without additional confirmation, as evidenced by the high trade count (176) and low win rate (36.9%). The Chandelier exit is doing most of the heavy lifting by letting winners run, but with Profit Factor only 1.48, the edge is thin.
>
> The concept is valid — Bull Power measures buyer control above the EMA mean — but it needs a filter to reduce noise signals. Compare with #126 (Elder Ray + ATR expansion on BTC) which shows the ATR expansion filter dramatically improves signal quality.
>
> **Minimum viable improvement: add ATR expansion filter. REVIEW — not ready for paper trading without signal enhancement.**
