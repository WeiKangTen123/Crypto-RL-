---
status: BAD
id: 80
sharpe: -0.47
return: -36.5
mdd: 47.2
win_rate: 30.8
trades: 52
pf: 0.60
---
# Stage 03 Backtest Report: SupertrendProStrategy (ID 80)

## 1. Performance Table

| Metric | Value |
| :--- | :--- |
| **Sharpe Ratio** | -0.47 |
| **Total Return** | -36.5% |
| **Max Drawdown** | 47.2% |
| **Win Rate** | 30.8% |
| **Total Trades** | 52 |
| **Profit Factor** | 0.60 |

---

## 2. Stability & Robustness

### Parameter Stability Test (Perturbations +/-10%)
The parameter stability test perturbed the strategy parameters by ±10% to check for parameter sensitivity:
- **rsi_period** (Baseline: 14)
  - -10% (13): Sharpe = -0.470
  - +10% (15): Sharpe = -0.470
- **rsi_low** (Baseline: 30)
  - -10% (27): Sharpe = -0.470
  - +10% (33): Sharpe = -0.470
- **rsi_high** (Baseline: 70)
  - -10% (63): Sharpe = -0.470
  - +10% (77): Sharpe = -0.470

*Stability Assessment*: The strategy's performance is completely invariant to ±10% parameter perturbations, remaining exactly at Sharpe -0.470. While this shows high "stability" in a mathematical sense, it indicates that these parameters are not active/effective constraints in the entry/exit logic, or the strategy is stuck in a flat region of poor performance.

### Cross-Asset Stress Test
We ran the strategy with the same parameters on secondary assets (using the 4h timeframe):
- **ETH**: Sharpe = -0.760, Trades = 51, Total Return = -61.13%
- **BTC (Primary)**: Sharpe = -0.470, Trades = 52, Total Return = -36.45%

*Cross-Asset Assessment*: The strategy fails the cross-asset stress test. Performance worsens on ETH to Sharpe -0.760 and drawdown increases to 71.2%, indicating that the strategy's underlying edge is fundamentally weak and does not possess global validity.

---

## 3. Expert Commentary

### Trade Character
With 52 trades over the backtest period on the 4h timeframe, the trade frequency is moderate (about 1 trade every 35 days). The win rate of 30.8% and profit factor of 0.60 indicate that the strategy suffers from a large proportion of losing trades with average losses exceeding average wins, resulting in a steady decay of capital.

### Chop Warnings
SupertrendProStrategy is designed to follow macro trends using Supertrend lines combined with RSI boundaries. However, on the 4h timeframe, this logic suffers from substantial lag. During choppy or range-bound consolidation phases, the strategy frequently opens trend-following positions right at the breakout exhaustion point, only to be stopped out as the market reverses, causing heavy whipsaw losses.

### Hypothesis Alignment
The original hypothesis suggested that combining a macro Supertrend filter with short-term RSI bounds would allow the strategy to join established trends at local oversold/overbought pullbacks. In practice, the RSI thresholds (30/70) combined with the 4h Supertrend are too lagging and fail to capture true pullbacks, leading to entries during momentum exhaustions instead. Additional volume filters or dynamic thresholds are needed.
