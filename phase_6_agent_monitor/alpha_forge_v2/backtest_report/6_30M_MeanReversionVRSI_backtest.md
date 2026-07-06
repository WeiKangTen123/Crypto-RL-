---
status: BAD
id: 6_30M
sharpe: 0.23
return: 7.3
mdd: 12.8
win_rate: 38.2
trades: 34
pf: 1.27
---
# Stage 03 Backtest Report: MeanReversionVRSI (ID: 6_30M)

## Performance Table

| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | 0.23 |
| **Total Return** | 7.30% |
| **Max Drawdown (MDD)** | 12.80% |
| **Win Rate** | 38.20% |
| **Total Trades** | 34 |
| **Profit Factor (PF)** | 1.27 |

## Stability & Robustness

### 1. Parameter Stability Test
* **Status**: **FAILED** (Highly Sensitive)
* **Details**: Perturbation testing of numerical parameters by ±10% was performed, revealing high sensitivity to key parameters:
  - `vrsi_period` (baseline 13): -10% change (to 12) resulted in a Sharpe of **0.160**; +10% change (to 14) resulted in a Sharpe of **0.200**.
  - `vwap_period` (baseline 184): -10% change (to 166) crashed the Sharpe to **-0.380**; +10% change (to 202) crashed the Sharpe to **-0.040**.
  - **Reason**: The strategy is highly sensitive to the VWAP reset period; a ±10% shift results in a complete collapse of profitability, showing the parameters sit on a fragile local peak.

### 2. Cross-Asset Stress Test
* **Status**: **FAILED**
* **Details**: Running the same parameters on secondary assets shows a lack of global validity:
  - **ETH (30m)**: Sharpe Ratio **-1.060** | Total Return **-28.60%** | Max Drawdown **28.60%** | Trades: **29**.
  - **BTC (30m)**: Sharpe Ratio **0.230** | Total Return **7.30%** | Max Drawdown **12.80%** | Trades: **34**.
  - **Reason**: The optimized parameters are highly asset-specific to BTC and do not transfer profitably to ETH, resulting in significant losses.

## Expert Commentary

### Trade Character
With only 34 trades executed over the 5-year period on the 30m timeframe, the trading frequency is extremely low. Although the profit factor is a healthy 1.27, the sample size is too small to represent a statistically significant edge. The entry signals are highly restrictive.

### Chop Warnings
As a mean-reversion strategy based on Volume RSI (VRSI) extremes and VWAP resets, it thrives in range-bound environments. However, because the optimized parameter set deactivated the ADX filter (`entry_filter` changed from `"ADX_BLOCKER"` to `"NONE"`), the strategy has no trend protection. In strongly trending markets, it will enter premature reversion trades and suffer severe drawdowns.

### Hypothesis Alignment
The core hypothesis of entering trades when volume-adjusted momentum reaches exhaustion (measured by VRSI) and exiting at the VWAP reset is sound. However, removing the ADX filter makes the strategy vulnerable to trend extensions. Combined with the high parameter sensitivity of `vwap_period` and cross-asset failure, the optimized setup is overfitted to BTC's local price movements and is not robust enough for production deployment.
