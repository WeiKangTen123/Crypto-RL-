---
status: BAD
id: 95
sharpe: -0.69
return: -80.2
mdd: 83.8
win_rate: 31.4
trades: 1015
pf: 0.83
---
# Stage 03 Backtest Report: ChoppinessKeltnerBreakoutStrategy (ID 95)

## 1. Performance Table

| Metric | Value |
| :--- | :--- |
| **Sharpe Ratio** | -0.69 |
| **Total Return** | -80.2% |
| **Max Drawdown** | 83.8% |
| **Win Rate** | 31.4% |
| **Total Trades** | 1015 |
| **Profit Factor** | 0.83 |

---

## 2. Stability & Robustness

### Parameter Stability Test (Perturbations +/-10%)
The parameter stability test perturbed the strategy parameters by ±10% to check for parameter sensitivity:
- **chop_period** (Baseline: 14)
  - -10% (13): Sharpe = -0.640
  - +10% (15): Sharpe = -0.530
- **kc_period** (Baseline: 20)
  - -10% (18): Sharpe = -0.940
  - +10% (22): Sharpe = -0.810
- **kc_mult** (Baseline: 2.0)
  - -10% (1.8): Sharpe = -0.860
  - +10% (2.2): Sharpe = -0.550
- **chop_threshold** (Baseline: 50.0)
  - -10% (45.0): Sharpe = -0.660
  - +10% (55.0): Sharpe = -0.760
- **sl_atr_multiplier** (Baseline: 2.6586)
  - -10% (2.3927): Sharpe = -0.690
  - +10% (2.9245): Sharpe = -0.680

*Stability Assessment*: The strategy exhibits structural unprofitability across all parameter variations. While minor perturbations do not result in a dramatic divergence in results (remaining consistently negative between -0.53 and -0.94), the lack of parameter configurations yielding positive Sharpe ratios indicates that the model has no positive mathematical expectancy.

### Cross-Asset Stress Test
We ran the strategy with the same parameters on secondary assets (using the 1h timeframe):
- **ETH**: Sharpe = -0.520, Trades = 1046, Total Return = -83.9%
- **BTC (Primary)**: Sharpe = -0.690, Trades = 1015, Total Return = -80.2%

*Cross-Asset Assessment*: The strategy fails the cross-asset stress test. Performance is consistently bad on both BTC and ETH, showing that the structural weakness of the alpha factor is universal and not coin-specific.

---

## 3. Expert Commentary

### Trade Character
With 1015 trades over the backtest period on the 1h timeframe, the strategy has an extremely high trade frequency (approx. 1 trade every 2 days). The average trade duration is short, resulting in significant transaction fee drag (given the trading fees and slippage parameters). The combination of a low win rate (31.4%) and small average wins leads to a steady downward equity curve, indicative of constant whipsawing.

### Chop Warnings
The strategy relies on the Choppiness Index (CHOP) to filter trades, intending to only take breakouts when the market is consolidated (high CHOP) and avoiding entries when the market is already trending (low CHOP). However, on the 1h timeframe, the Choppiness Index appears to be a lagging indicator. The breakout entries occur too late—often at the tail end of short-term volatility expansions—resulting in buying local tops and selling local bottoms. This causes severe chop loss.

### Hypothesis Alignment
The original alpha hypothesis predicted that combining the Choppiness Index with Keltner Channel breakouts would allow the model to enter during high-momentum breakout regimes. However, the data contradicts this hypothesis. The Keltner Channel boundaries are frequently breached by temporary market noise, and without additional filters (such as volume, trend direction, or order flow imbalance), the strategy is structurally unprofitable due to transaction fee drag and false breakouts.
