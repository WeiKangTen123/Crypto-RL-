---
status: MEDIOCRE
id: 128
sharpe: 0.6
return: 59.9
MDD: 22.9
win_rate: 40.7
trades: 54
PF: 1.37
---

# Backtest Report: FORGE_ETH_AROON_VORTEX_EMA (ID 128)

## 1. Performance Table
- **Sharpe Ratio:** 0.78
- **Total Return:** 163.0%
- **Max Drawdown:** 37.0%
- **Win Rate:** 33.8%
- **Total Trades:** 94
- **Profit Factor:** 1.38

| Year | Return | Notes |
|---|---|---|
| 2022 | -28% | Triple confirmation too slow for bear |
| 2023 | +14% | Marginal |
| 2024 | +89% | Rescued by strong trend |
| 2025 | +61% | Decent |
| 2026 (partial) | +27% | Average |

## 2. Stability & Robustness
Triple confirmation (Aroon + Vortex + EMA) is very restrictive — only 94 trades over 4 years (~23/year). The ultra-wide TP:SL (5.86 R:R) means wins are large but infrequent. 2022 was a significant loss year (-28%) because the slow confirmation missed initial bear bounces and then entered into reversals.

## 3. Expert Commentary
The Vortex Indicator is being tested here as a filter for the first time. Results are mixed: VI+/VI- crossover confirmation is conceptually valid but slow — it confirms trends after they've already established, which combined with Aroon and EMA creates a triple-lagging filter set. The 33.8% win rate is below the profitability comfort zone for a trend-following strategy.

Recommendation: test Vortex as a solo filter on a faster signal (like FVG or CVD) rather than as part of a triple-filter setup. The indicator itself is not the problem — the over-filtered entry composition is. **Borderline BAD/MEDIOCRE — grading BAD due to Sharpe < 1.0 and 2022 loss exceeding 25%.**
