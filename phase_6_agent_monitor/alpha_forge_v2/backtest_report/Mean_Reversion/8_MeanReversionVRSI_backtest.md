---
status: MEDIOCRE
id: 8
sharpe: 0.65
return: 51.31
mdd: 11.12
win_rate: 64.15
trades: 53
pf: 1.78
---
# Stage 03 Backtest Report: MeanReversionVRSI (ID: 8)

## Performance Table

| Metric | Value |
| --- | --- |
| **Sharpe Ratio** | 0.65 |
| **Total Return** | 51.31% |
| **Max Drawdown (MDD)** | 11.12% |
| **Win Rate** | 64.15% |
| **Total Trades** | 53 |
| **Profit Factor (PF)** | 1.78 |

## Stability & Robustness

### 1. Parameter Stability Test
* **Status**: **FAILED** (High Fragility)
* **Details**: Perturbation testing of numerical parameters by ±10% revealed high sensitivity around certain key thresholds:
  - `vrsi_overbought` (baseline 87.7028): Perturbing by -10% (to 78.9325) crashed the Sharpe Ratio from **0.65** to **-0.21**. This indicates that the strategy's profitability is highly sensitive to the exact overbought threshold chosen.
  - `vwap_std_mult` (baseline 3.0629): Perturbing by +10% (to 3.3692) dropped the Sharpe Ratio to **0.25** (a drop greater than 50% from baseline).
  - Variations in other parameters (`vrsi_period`, `vrsi_oversold`, `vwap_period`, `sl_pct`, `ema_period`) showed acceptable stability, but the overbought threshold fragility remains a critical risk.

### 2. Cross-Asset Stress Test
* **Status**: **FAILED** (Asset Specific)
* **Details**: Running the same optimized parameters on secondary assets shows clear lack of global validity:
  - **ETH (1h)**: Sharpe Ratio **-1.04** | Total Return **-69.33%** | Max Drawdown **72.53%** | Trades: 64.
  - The strategy is heavily optimized for BTC's specific volatility and volume profile and should not be run on ETH or other altcoins without individual tuning.

## Expert Commentary

### Trade Character
With a profit factor of 1.78 and a win rate of 64.15%, the strategy displays highly selective trade execution. Over the 5.4-year backtest period, it generated only 53 trades. This extremely low trade frequency (~10 trades per year) raises concerns regarding statistical significance (CLT minimum is 30, so 53 is technically valid but thin) and suggests the strategy is curve-fitted to specific market conditions rather than capturing a broad, recurring edge.

### Chop Warnings
As a mean reversion strategy relying on standard deviation bands from VWAP, the strategy is highly vulnerable to prolonged sideways chop containing high volatility spikes that don't mean-revert. The `use_trend_filter` parameter set to `True` helps to filter out some trend-continuation moves, but the narrowness of the VRSI overbought threshold means that in choppy regimes, it may trigger false signals or completely freeze.

### Hypothesis Alignment
The original researcher hypothesis suggested that incorporating volume weightings to the standard RSI (VRSI) would provide a cleaner signal of exhaustion at local extremes. The primary backtest on BTC supports this, achieving a 0.65 Sharpe. However, the extreme parameter fragility (where a -10% change in the overbought threshold turns the strategy unprofitable) and the -1.04 Sharpe on ETH indicate that the hypothesis lacks structural robustness and acts more like a custom BTC filter than a general market edge.
