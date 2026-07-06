---
status: BAD
id: 180
sharpe: -0.55
return: -2.08
mdd: 2.64
win_rate: 57.6
trades: 125
pf: 0.83
---
# Stage 03 Backtest Report: GridTradingBTCStrategy (ID: 180)

## Performance Table

| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | -0.55 |
| **Total Return** | -2.08% |
| **Max Drawdown (MDD)** | 2.64% |
| **Win Rate** | 57.6% |
| **Total Trades** | 125 |
| **Profit Factor (PF)** | 0.83 |

## Stability & Robustness

### 1. Parameter Stability Test
* **Status**: **PASSED** (but remains unprofitable)
* **Details**: Perturbation testing of numerical parameters by ±10% was performed. The strategy remains consistently unprofitable with little change in Sharpe:
  - `grid_spacing` (baseline 1000): ±10% change (900 and 1100) resulted in unchanged Sharpe of **-0.55**.
  - `order_size` (baseline 0.001): ±10% change resulted in unchanged Sharpe of **-0.55**.
  - `stop_loss_pct` (baseline 0.0437): -10% change (to 0.0393) dropped Sharpe to **-0.57**; +10% change (to 0.0481) improved Sharpe slightly to **-0.26**.
  - `initial_balance` (baseline 10000): ±10% change resulted in unchanged Sharpe of **-0.55**.

### 2. Cross-Asset Stress Test
* **Status**: **FAILED** (Absolute Levels Hardcoded)
* **Details**: Running the same parameters on secondary assets shows a fundamental structural issue:
  - **ETH (4h)**: Sharpe Ratio **0.00** | Total Return **0.00%** | Max Drawdown **0.00%** | Trades: **0**.
  - **Reason**: The grid levels `[28000, 29000, 30000, 31000, 32000]` are hardcoded to BTC's nominal price scale. Since ETH's nominal price has never reached 28,000 USD, no buy or sell orders were ever triggered. This indicates zero cross-asset validity.

## Expert Commentary

### Trade Character
With a profit factor of 0.83 and 125 trades over 5 years on BTC/4h, the trade execution frequency is moderate. However, the profit factor below 1.0 indicates that the strategy is structurally unprofitable under the current setup. The strategy accumulates positions on the way down but fails to exit them profitably, leading to fee drag and a slow equity bleed.

### Chop Warnings
A grid trading strategy depends on range-bound choppy markets to succeed. However, because these grid levels are completely static, any sustained trend (breakout or breakdown) will result in the strategy being either left behind (exiting too early in an uptrend) or caught holding a large volume of underwater inventory (buying all the way down in a downtrend).

### Hypothesis Alignment
The original hypothesis of using grid-spacing to capture micro-fluctuations in range-bound environments is valid, but hardcoding absolute nominal price levels is a critical design failure. The strategy fails on secondary assets and becomes obsolete once the price exits the 28k–32k band. The hypothesis must be refactored to utilize percentage-based or ATR-based dynamic bands rather than fixed USD levels to have any chance of global validity.
