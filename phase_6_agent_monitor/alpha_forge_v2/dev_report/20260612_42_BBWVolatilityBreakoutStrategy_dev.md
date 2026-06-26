---
status: IMPLEMENTED
id: 42
class: BBWVolatilityBreakoutStrategy
coin: BTC
timeframe: 1h
sharpe: 1.26
return: 35.2
MDD: 18.0
win_rate: 30.9
trades: 188
PF: 1.4
date: 20260612
recommendation: PASS
---

# Dev Report: BBWVolatilityBreakoutStrategy (ID 42)

**Alpha Hypothesis:** Low-volatility squeeze followed by expansion breakout
**Strategy Type:** Volatility Breakout
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 42

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.26 |
| Total Return | 35.2% |
| Max Drawdown | 18.0% |
| Win Rate | 30.9% |
| Total Trades | 188 |
| Profit Factor | 1.4 |
| Avg Hold Duration | — |
| Period | 2023-01-01 → 2024-01-01 |
| Coin / Timeframe | BTC / 1h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 1h | 1.26 | ✅ Primary — confirmed |
| BTC / 4h | — | ⏳ Pending cross-asset run |
| ETH / 1h | — | ⏳ Pending cross-asset run |

**Note:** Cross-asset validation is pending for this backfill report. Run `strategy-tuner` cross-asset check to complete section 2.

---

## 3. Trade Character

**Long/Short Split:** Data from primary backtest period.
**Avg Hold Duration:** —

### Sample Trades

| # | Date | Side | Entry | Exit | PnL | Notes |
|---|---|---|---|---|---|---|
| 1 | 2023-01-03 | 🔴 SHORT | $16,614.27 | $16,710.32 | -$6.28 | Signal triggered — EXIT exit |
| 2 | 2023-01-08 | 🟢 LONG | $17,008.93 | $16,928.40 | -$5.2 | Signal triggered — EXIT exit |
| 3 | 2023-01-10 | 🟢 LONG | $17,336.36 | $17,409.85 | +$3.69 | Signal triggered — EXIT exit |
| 4 | 2023-01-11 | 🔴 SHORT | $17,323.76 | $17,495.83 | -$10.34 | Signal triggered — EXIT exit |
| 5 | 2023-01-11 | 🟢 LONG | $17,559.07 | $17,989.56 | +$23.52 | Signal triggered — EXIT exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Low-volatility squeeze followed by expansion breakout
**Regime Label:** Breakout

The equity curve reflects performance across BTC/ETH market cycles from 2023-01-01 to 2024-01-01, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- BBW squeeze detection can fire late — enters after initial breakout impulse
- In strong trending markets, squeeze signals are rare — low trade frequency
- False breakouts in news-driven spikes can trigger SL immediately

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.26 meets the GOOD threshold. Trade count of 188 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 42` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
