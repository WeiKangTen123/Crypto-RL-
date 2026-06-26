---
status: IMPLEMENTED
id: {STRATEGY_ID}
class: {STRATEGY_CLASS}
coin: {COIN}
timeframe: {TIMEFRAME}
sharpe: {SHARPE}
return: {TOTAL_RETURN}
MDD: {MAX_DRAWDOWN}
win_rate: {WIN_RATE}
trades: {TOTAL_TRADES}
PF: {PROFIT_FACTOR}
date: {YYYYMMDD}
recommendation: {PASS|CONDITIONAL_PASS|REJECT}
---

# Dev Report: {STRATEGY_CLASS} (ID {STRATEGY_ID})

**Alpha Hypothesis:** {One-line description of the edge being exploited — e.g. "Exploits mean-reversion after RSI divergence confirmed by volume exhaustion"}
**Built by:** @alpha-developer
**Date:** {YYYY-MM-DD}
**Registered:** `settings.py` ID {STRATEGY_ID}

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | {SHARPE} |
| Total Return | {TOTAL_RETURN}% |
| Max Drawdown | {MAX_DRAWDOWN}% |
| Win Rate | {WIN_RATE}% |
| Total Trades | {TOTAL_TRADES} |
| Profit Factor | {PROFIT_FACTOR} |
| Avg Hold Duration | {AVG_HOLD_DAYS}d |
| Period | {DATE_FROM} → {DATE_TO} |

---

## 2. Cross-Asset Consistency

| Asset / TF | Sharpe | Return | MDD | Trades | Verdict |
|---|---|---|---|---|---|
| BTC / 1h | {SHARPE} | {RETURN}% | {MDD}% | {TRADES} | ✅ Primary |
| BTC / 4h | {SHARPE} | {RETURN}% | {MDD}% | {TRADES} | {✅ Consistent / ⚠ Weaker / ❌ Breaks} |
| ETH / 1h | {SHARPE} | {RETURN}% | {MDD}% | {TRADES} | {✅ Consistent / ⚠ Weaker / ❌ Breaks} |

**Consistency Verdict:** {e.g. "Alpha holds across all three — factor is not BTC-specific" OR "Only works on BTC/1h — likely overfitted to BTC microstructure"}

---

## 3. Trade Character

**Long/Short Split:** {X}% Long · {Y}% Short
**Avg Hold Duration:** {N} bars ({H} hours)
**Best Trade:** +${BEST_USD} ({BEST_PCT}%) · **Worst Trade:** -${WORST_USD} ({WORST_PCT}%)

### Sample Trades (3–5 representative examples)

| # | Date | Side | Entry | Exit | PnL | Reasoning |
|---|---|---|---|---|---|---|
| 1 | {DATE} | LONG | ${ENTRY} | ${EXIT} | +${PNL} | {e.g. "RSI(14) crossed below 28, ADX > 22, taker ratio > 0.62 — momentum exhaustion signal confirmed"} |
| 2 | {DATE} | SHORT | ${ENTRY} | ${EXIT} | -${PNL} | {e.g. "Signal fired but ADX < 15 (choppy market) — regime filter failed to block entry"} |
| 3 | {DATE} | LONG | ${ENTRY} | ${EXIT} | +${PNL} | {e.g. "Clean trend day, EMA spread widening, exit at TP +3.5×ATR"} |

### Worst Trade Analysis
**Date:** {DATE} · **Loss:** -${LOSS} · **Reason:** {e.g. "Sharp news spike invalidated the mean-reversion setup — stop-loss triggered at -2.1%"}

---

## 4. Regime Behaviour

| Period | Market Condition | Equity Curve | Notes |
|---|---|---|---|
| 2023 Q1 | Bear / Choppy | {Flat / Declining / Rising} | {e.g. "Strategy struggles in sub-20 ADX regimes"} |
| 2023 Q2–Q4 | Recovery Trend | {Flat / Declining / Rising} | {e.g. "Strong performance during trending recovery"} |
| 2024 | Bull Run | {Flat / Declining / Rising} | {e.g. "Reduced trade frequency — signal fires less often in strong trend"} |
| 2025 | Volatile / Mixed | {Flat / Declining / Rising} | {e.g. "Best period — volatility expansion suits the strategy"} |

**Optimal Regime:** {e.g. "Ranging-to-volatile markets with ADX 20–35. Underperforms in extreme trends (ADX > 40)."}

---

## 5. Known Weaknesses

- {e.g. "Stop-loss is ATR-based — in low-volatility regimes, stops are too tight and get clipped by noise"}
- {e.g. "Long bias — only 30% short trades; underperforms in prolonged bear markets"}
- {e.g. "High trade frequency increases fee drag — needs Optuna to tune entry filters tighter"}

---

## 6. Developer Recommendation

**Verdict: {PASS / CONDITIONAL PASS / REJECT}**

> {Professional 2–3 sentence summary. Example:
> "Baseline Sharpe of 1.15 on BTC/1h is statistically meaningful at 271 trades. Cross-asset check confirms the alpha is not BTC-specific — ETH/1h shows Sharpe 0.82. Regime filter correctly gates entries during ADX < 15 chop. Ready for Optuna fine-tuning — recommend tuning `rsi_period`, `atr_multiplier`, and `sl_pct` first."}

**Suggested Optuna Priority Params:** `{param_1}`, `{param_2}`, `{param_3}`
