---
status: BAD
id: 79
sharpe: -0.35
return: -42.0
mdd: 63.6
win_rate: 18.8
trades: 516
pf: 0.88
---
# Stage 03 Backtest Report: GoldenZoneFibBOSStrategy (ID 79)

## 1. Performance Table

| Metric | Value |
| :--- | :--- |
| **Sharpe Ratio** | -0.35 |
| **Total Return** | -42.0% |
| **Max Drawdown** | 63.6% |
| **Win Rate** | 18.8% |
| **Total Trades** | 516 |
| **Profit Factor** | 0.88 |

---

## 2. Stability & Robustness

### Parameter Stability Test (Perturbations +/-10%)
The parameter stability test perturbed the strategy parameters by ±10% to check for parameter sensitivity:
- **swing_window** (Baseline: 20)
  - -10% (18): Sharpe = -0.82
  - +10% (22): Sharpe = -0.28
- **fib_retrace** (Baseline: 0.618)
  - -10% (0.5562): Sharpe = -0.42
  - +10% (0.6798): Sharpe = -0.27
- **fib_ext** (Baseline: 1.618)
  - -10% (1.4562): Sharpe = -0.39
  - +10% (1.7798): Sharpe = -0.60
- **sl_fib** (Baseline: 0.786)
  - -10% (0.7074): Sharpe = -0.44
  - +10% (0.8646): Sharpe = -0.29
- **rsi_period** (Baseline: 14)
  - -10% (13): Sharpe = -0.38
  - +10% (15): Sharpe = -0.34
- **rsi_long** (Baseline: 50)
  - -10% (45): Sharpe = -0.31
  - +10% (55): Sharpe = -0.38
- **rsi_short** (Baseline: 50)
  - -10% (45): Sharpe = -0.31
  - +10% (55): Sharpe = -0.51

*Stability Assessment*: The strategy is structurally unprofitable across all tested parameters, with Sharpe ratios ranging from -0.82 to -0.27. Varying `swing_window` downward to 18 resulted in a severe performance drop to -0.82, highlighting parameter fragility.

### Cross-Asset Stress Test
We ran the strategy with the same parameters on secondary assets (using the 1h timeframe):
- **ETH**: Sharpe = 0.26, Trades = 515, Total Return = 19.65%
- **BTC (Primary)**: Sharpe = -0.35, Trades = 516, Total Return = -42.04%

*Cross-Asset Assessment*: Although the strategy is unprofitable on BTC, it shows marginally positive results on ETH (Sharpe 0.26, Return +19.65%). However, the high trade count (515) and thin Sharpe indicate it lacks a robust global edge and is highly regime-dependent.

---

## 3. Expert Commentary

### Trade Character
With 516 trades on the 1h timeframe, this strategy trades quite frequently (around 1 trade every 4 days). The extremely low win rate of 18.8% combined with a Profit Factor of 0.88 leads to a grinding down of equity due to fee drag and a high number of consecutive small losses.

### Chop Warnings
The Golden Zone Fibonacci entry rules aim to capture pullbacks within a established Break of Structure (BOS) trend. However, in choppy or range-bound markets, the BOS signals frequently result in false breakouts, leading the strategy to buy the top or sell the bottom of local consolidations. The rsi filter at 50 is too simple and fails to prevent entry during these periods of high noise.

### Hypothesis Alignment
The original hypothesis predicted that entering at the Fibonacci 0.618 golden ratio after a Break of Structure would capture high-expectancy trend continuations. In reality, the Keltner or swing-based structures are highly noisy on the 1h timeframe, leading to false BOS signals. Without volume confirmation or trend strength gating (like ADX), the entries are premature and suffer from heavy whipsaw.
