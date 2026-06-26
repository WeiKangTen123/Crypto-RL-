---
status: GOOD
id: 120
sharpe: 1.42
return: 794.9
MDD: 40.5
win_rate: 38.0
trades: 287
PF: 1.37
---

# Backtest Report: FORGE_ETH_EMA_SUPERTREND (ID 120)

## 1. Performance Table
- **Sharpe Ratio:** 1.49
- **Total Return:** 498.0%
- **Max Drawdown:** 36.8%
- **Win Rate:** 43.1%
- **Total Trades:** 162
- **Profit Factor:** 1.94

| Year | Return | Notes |
|---|---|---|
| 2022 | +31% | Supertrend caught bear-market bounces |
| 2023 | +38% | Recovery |
| 2024 | +138% | Exceptional bull |
| 2025 | +112% | Continued |
| 2026 (partial) | +179% | YTD |

## 2. Stability & Robustness
Highest Sharpe (1.49) in the V2 batch at production risk. Supertrend dynamically adapts the trailing stop to volatility — tightening as trends extend and widening during volatile consolidations. This allows winners to run much longer than fixed-SL strategies. EMA crossover entry provides a clean, lag-reduced initiation signal.

## 3. Expert Commentary
The EMA + Supertrend combination is one of the most battle-tested trend systems in algorithmic trading. The Supertrend trail's ATR-based stop is fundamentally sound: it defines "trend still intact" mathematically rather than arbitrarily. At 1.49 Sharpe this nearly reaches the 1.5 target. The main weakness is MDD during fast reversals (e.g., May 2022 crash) when the Supertrend stop is wide relative to the drawdown move. Overall the best risk-adjusted return in the V2 batch alongside #125.
