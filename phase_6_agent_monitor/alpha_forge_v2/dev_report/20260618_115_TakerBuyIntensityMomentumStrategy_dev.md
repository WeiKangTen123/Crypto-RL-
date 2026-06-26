---
status: BAD
id: 115
sharpe: -2.93
return: -91.4
MDD: 91.6
win_rate: 25.1
trades: 1352
PF: 0.85
date: 20260618
recommendation: REJECT
---

# Dev Report: TakerBuyIntensityMomentumStrategy (ID 115)

**Alpha Hypothesis:** Taker Buy Intensity Momentum
**Strategy Type:** Order Flow / Trend Following
**Built by:** @alpha-developer
**Date:** 2026-06-18
**Registered:** `settings.py` ID 115

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | -2.93 |
| Total Return | -91.4% |
| Max Drawdown | 91.6% |
| Win Rate | 25.1% |
| Total Trades | 1352 |
| Profit Factor | 0.85 |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | -2.93 | ❌ Primary — failed |

---

## 3. Developer Recommendation

**Verdict: REJECT**

> The Taker Buy Ratio threshold (0.55+) generates too many false positive breakout signals. By trading exactly at the moment of peak "taker buy intensity", the strategy often enters at the top of local liquidity hunts, resulting in massive whipsaws. The 10x leverage and over-trading (1352 trades) destroyed the account (-91.4% return, 91.6% MDD). The exit logic also needs overhaul to catch runners rather than getting chopped.
