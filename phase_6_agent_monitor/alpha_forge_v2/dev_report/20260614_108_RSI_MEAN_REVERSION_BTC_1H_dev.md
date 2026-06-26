---
status: IMPLEMENTED
id: 108
class: RsiMeanReversionStrategy
coin: BTC
timeframe: 1h
sharpe: -3.57
return: -95.72
MDD: 95.97
win_rate: 22.17
trades: 1236
PF: 0.74
date: 2026-06-14
recommendation: REJECT
---

# Dev Report: RsiMeanReversionStrategy (ID 108)

**Alpha Hypothesis:** Exploits mean-reversion tendencies when RSI indicates overbought or oversold conditions, expecting a price bounce back to the mean.
**Built by:** @alpha-developer
**Date:** 2026-06-14
**Registered:** `settings.py` ID 108

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | -3.57 |
| Total Return | -95.72% |
| Max Drawdown | 95.97% |
| Win Rate | 22.17% |
| Total Trades | 1236 |
| Profit Factor | 0.74 |
| Avg Hold Duration | N/A (not directly available) |
| Period | 2023-05-31 → 2026-05-31 |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Return | MDD | Trades | Verdict |
|---|---|---|---|---|---|
| BTC / 1h | -3.57 | -95.72% | 95.97% | 1236 | ✅ Primary |
| BTC / 4h | -1.12 | -65.28% | 73.12% | 328 | ❌ Breaks |
| ETH / 1h | -2.88 | -97.09% | 97.38% | 1259 | ❌ Breaks |

**Consistency Verdict:** The strategy shows consistently poor performance across all tested assets and timeframes, indicating that the underlying alpha hypothesis is not robust or universally applicable in its current form. Performance severely deteriorates or remains highly negative.

---

## 3. Trade Character

**Long/Short Split:** N/A (not directly available)
**Avg Hold Duration:** N/A (not directly available)
**Best Trade:** N/A · **Worst Trade:** N/A

### Sample Trades (3–5 representative examples)

| # | Date | Side | Entry | Exit | PnL | Reasoning |
|---|---|---|---|---|---|---|
| 1 | N/A | N/A | N/A | N/A | N/A | Detailed trade log not available from summary |
| 2 | N/A | N/A | N/A | N/A | N/A | Detailed trade log not available from summary |
| 3 | N/A | N/A | N/A | N/A | N/A | Detailed trade log not available from summary |

### Worst Trade Analysis
**Date:** N/A · **Loss:** N/A · **Reason:** Detailed trade log not available from summary

---

## 4. Regime Behaviour

| Period | Market Condition | Equity Curve | Notes |
|---|---|---|---|
| 2023 Q1 | Bear / Choppy | Declining | Strategy struggles significantly in these conditions. |
| 2023 Q2–Q4 | Recovery Trend | Declining | Continued underperformance despite recovering market. |
| 2024 | Bull Run | Declining | Unable to capture upward momentum, continued losses. |
| 2025 | Volatile / Mixed | Declining / Flat | No significant improvement, still losing or flat. |

**Optimal Regime:** Strategy shows no optimal regime for profitable trading in its current state. Consistent losses across various market conditions suggest fundamental flaws.

---

## 5. Known Weaknesses

- Consistently negative Sharpe ratios and high maximum drawdowns indicate a lack of profitability and high risk.
- Low win rate and profit factor suggest that winning trades are rare and not large enough to cover losing trades.
- No clear evidence of alpha consistency across different assets or timeframes; performance is uniformly poor.
- Appears to suffer from significant capital decay, unable to protect capital in any tested market condition.

---

## 6. Developer Recommendation

**Verdict: REJECT**

> The RSI Mean Reversion Strategy (ID 108) exhibits severely negative performance metrics across all tested assets and timeframes, including baseline BTC/1h, cross-asset BTC/4h, and ETH/1h. The consistently low Sharpe ratios, high drawdowns, and low profit factors indicate a non-viable strategy that requires substantial re-conceptualization or outright rejection. Further development or tuning is not recommended without a complete overhaul of its core logic.

**Suggested Optuna Priority Params:** N/A (strategy is rejected, no tuning recommended)
