---
status: IMPLEMENTED
id: 30
class: LiquiditySweepReversalStrategy
coin: BTC
timeframe: 4h
sharpe: 1.28
return: 204.3
MDD: 24.6
win_rate: 13.8
trades: 275
PF: 0.73
date: 20260612
recommendation: PASS
---

# Dev Report: LiquiditySweepReversalStrategy (ID 30)

**Alpha Hypothesis:** Ranging or choppy markets where liquidity sweeps occur
**Strategy Type:** Mean Reversion / Structure
**Built by:** @alpha-developer
**Date:** 2026-06-12
**Registered:** `settings.py` ID 30

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.28 |
| Total Return | 204.3% |
| Max Drawdown | 24.6% |
| Win Rate | 13.8% |
| Total Trades | 275 |
| Profit Factor | 0.73 |
| Avg Hold Duration | — |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 10x |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Verdict |
|---|---|---|
| BTC / 4h | 1.28 | ✅ Primary — confirmed |
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
| 1 | 2023-01-06 | 🔴 SHORT | $16,849.24 | $17,048.86 | -$6.8 | Signal triggered — SL exit |
| 2 | 2023-01-09 | 🟢 LONG | $17,285.04 | $17,328.97 | +$27.96 | Signal triggered — TP exit |
| 3 | 2023-01-10 | 🔴 SHORT | $17,431.94 | $17,550.72 | -$7.41 | Signal triggered — SL exit |
| 4 | 2023-01-12 | 🔴 SHORT | $18,837.20 | $19,095.67 | -$14.3 | Signal triggered — SL exit |
| 5 | 2023-01-16 | 🔴 SHORT | $21,065.14 | $21,440.43 | -$18.14 | Signal triggered — SL exit |

---

## 4. Regime Behaviour

**Optimal Regime:** Ranging or choppy markets where liquidity sweeps occur
**Regime Label:** Ranging

The equity curve reflects performance across BTC/ETH market cycles from 2021-01-01 to 2026-05-31, including bull, bear, and ranging periods. Full regime breakdown requires visual equity curve inspection in the Phase 4 dashboard.

---

## 5. Known Weaknesses

- Low win rate (14%) means large drawdown strings are possible
- Liquidity sweeps can cascade in trending markets — strategy can fight the trend
- Requires adequate spread/liquidity; performance degrades on thin order books

---

## 6. Developer Recommendation

**Verdict: PASS**

> Baseline Sharpe of 1.28 meets the GOOD threshold. Trade count of 275 is adequate. Recommend Optuna tuning to push Sharpe above 1.5 before paper trading.

**Suggested Optuna Priority:** Run `finetune.py --strategy_id 30` to discover optimal parameters. Focus on signal threshold params and SL/TP multipliers first.
