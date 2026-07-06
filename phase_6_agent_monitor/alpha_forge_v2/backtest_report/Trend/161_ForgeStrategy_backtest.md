---
status: BAD
id: 161
sharpe: 0.16
return: -2.34
mdd: 47.28
win_rate: 21.88
trades: 713
pf: 1.0
---
# Stage 03 Backtest Report: ForgeStrategy (ID: 161)

## Performance Table

| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | 0.16 |
| **Total Return** | -2.34% |
| **Max Drawdown (MDD)** | 47.28% |
| **Win Rate** | 21.88% |
| **Total Trades** | 713 |
| **Profit Factor (PF)** | 1.00 |

## Stability & Robustness

### 1. Parameter Stability Test
* **Status**: **FAILED** (High Fragility)
* **Details**: Perturbation testing of numerical parameters by ±10% revealed high sensitivity around key thresholds:
  - `ema_fast` (baseline 25): Perturbing by -10% (to 22) crashed the Sharpe Ratio from **0.16** to **0.01**.
  - `ema_slow` (baseline 159): Perturbing by -10% (to 143) crashed the Sharpe Ratio to **-0.14** (becoming unprofitable).
  - `macd_fast` (baseline 14): Perturbing by +10% (to 15) crashed the Sharpe Ratio to **0.01**.
  - `macd_slow` (baseline 45): Perturbing by +10% (to 50) crashed the Sharpe Ratio to **0.07**.
  - `tp_atr_mult` (baseline 7.1303): Perturbing by ±10% crashed the Sharpe Ratio to **-0.38** (at 6.4173) and **-0.32** (at 7.8433).
  - `sl_atr_mult` (baseline 1.7169): Perturbing by ±10% crashed the Sharpe to **-0.02** (at 1.5452) and **-0.09** (at 1.8886).
  - `atr_period` (baseline 27): Perturbing by -10% (to 24) crashed the Sharpe to **0.05**.
  - The extreme sensitivity of these parameters suggests the model's performance relies on a highly overfitted parameter pocket rather than a stable, structural edge.

### 2. Cross-Asset Stress Test
* **Status**: **FAILED** (Asset Specific)
* **Details**: Running the same parameters on secondary assets shows complete lack of global validity:
  - **ETH (1h)**: Sharpe Ratio **-1.25** | Total Return **-90.68%** | Max Drawdown **92.47%** | Trades: 794.
  - The strategy is heavily overfitted to BTC-specific price dynamics and suffers catastrophic failure when applied to ETH.

## Expert Commentary

### Trade Character
With a profit factor of 1.00 and a win rate of 21.88%, the strategy relies on rare, high-payoff trends to offsets frequent small losses (typical of a trend-following crossover profile). The high trade count of 713 over the 3.4-year backtest period (~210 trades per year) is statistically representative. However, the overall return of -2.34% shows the strategy fails to yield any real net profitability, acting as an expensive churn mechanism rather than a viable source of alpha.

### Chop Warnings
As a pure EMA and MACD crossover model, the strategy is highly vulnerable to prolonged sideways chop. The high trade frequency and low win rate indicate the model is repeatedly whipsawed during market consolidation, leading to substantial fee drag (713 trades with a 0.0005 fee rate creates significant friction that erodes any minor gains).

### Hypothesis Alignment
The original hypothesis of using EMA-MACD crossover entry combined with ATR-based TP/SL to capture clean trend expansions is not confirmed by the data. A Sharpe Ratio of 0.16 on BTC demonstrates that simple momentum crossovers are insufficient without additional filters (such as volume gates, ADX filters, or volatility regimes). The catastrophic drawdown on ETH and extreme parameter fragility further suggest that the minor positive edge observed on BTC is transient and unstable.