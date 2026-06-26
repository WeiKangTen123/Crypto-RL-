---
status: IMPLEMENTED
id: 48
class: WaveTrendMFIDivergenceStrategy
coin: BTC
timeframe: 1h
sharpe: 1.32
return: 33.8
MDD: 6.5
win_rate: 52.2
trades: 23
PF: 3.14
date: 20260612
recommendation: PASS
---

# Dev Report: WaveTrendMFIDivergenceStrategy (ID 48)

**Alpha Hypothesis:** WaveTrend oscillator oversold/overbought with MFI divergence
**Strategy Type:** Mean Reversion / Divergence
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 48

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.32 |
| Total Return | 33.8% |
| Max Drawdown | 6.5% |
| Win Rate | 52.2% |
| Total Trades | 23 |
| Profit Factor | 3.14 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | 1.32 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation pending. Run `strategy-tuner` cross-asset check to complete.

---

## 3. Trade Character

**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-01-09 | 🔴 SHORT | $17,197.35 | $17,357.91 | -$9.84 | Signal triggered — SL exit |
| 2 | 2023-06-05 | 🟢 LONG | $26,742.00 | $26,340.69 | -$15.34 | Signal triggered — SL exit |
| 3 | 2023-09-06 | 🟢 LONG | $25,872.94 | $25,671.22 | -$8.08 | Signal triggered — SL exit |
| 4 | 2023-09-10 | 🟢 LONG | $25,812.90 | $25,447.32 | -$14.15 | Signal triggered — SL exit |
| 5 | 2023-11-27 | 🟢 LONG | $37,096.34 | $38,176.12 | +$27.18 | Signal triggered — TP exit |

---

## 4. Regime Behaviour

**Optimal Regime:** WaveTrend oscillator oversold/overbought with MFI divergence
**Regime Label:** Ranging

Performance spans 2021-01-01 → 2026-05-31, covering bull, bear, and ranging BTC/ETH cycles. Full regime breakdown available via Phase 4 dashboard equity curve.

---

## 5. Known Weaknesses

- Very low trade count (23) — statistically unreliable at current settings
- WaveTrend + MFI dual confirmation reduces entry frequency significantly
- Both indicators are mean-reversion focused — vulnerable in strong trends

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.32 meets the GOOD threshold. Trade count of 23 is on the lower side — Optuna fine-tuning should focus on improving signal frequency alongside quality.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 48` to find optimal parameters.
