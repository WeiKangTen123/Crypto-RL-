---
status: BAD
id: 136
sharpe: 0.16
return: 3.97
mdd: 23.82
win_rate: 27.88
trades: 104
pf: 1.06
---
# Stage 03 Backtest Report: AVSStrategy (ID 136)

## 1. Performance Table

| Metric | Value |
| :--- | :--- |
| **Sharpe Ratio** | 0.16 |
| **Total Return** | 3.97% |
| **Max Drawdown** | 23.82% |
| **Win Rate** | 27.88% |
| **Total Trades** | 104 |
| **Profit Factor** | 1.06 |

---

## 2. Stability & Robustness

### Parameter Stability Test (Perturbations +/-10%)
The parameter stability test perturbed the strategy parameters by ±10% to check for parameter sensitivity:
- **bb_period** (Baseline: 43)
  - -10% (39): Sharpe = -0.46
  - +10% (47): Sharpe = -0.75
- **bb_std** (Baseline: 1.4214)
  - -10% (1.2793): Sharpe = 0.13
  - +10% (1.5635): Sharpe = -0.68
- **intensity_period** (Baseline: 8)
  - -10% (7): Sharpe = 0.16
  - +10% (9): Sharpe = 0.16
- **intensity_std** (Baseline: 1.0682)
  - -10% (0.9614): Sharpe = 0.16
  - +10% (1.1750): Sharpe = 0.16
- **taker_threshold** (Baseline: 0.6796)
  - -10% (0.6116): Sharpe = 0.16
  - +10% (0.7476): Sharpe = 0.16
- **sl_atr_mult** (Baseline: 0.8911)
  - -10% (0.8020): Sharpe = 0.16
  - +10% (0.9802): Sharpe = 0.16
- **tp_atr_mult** (Baseline: 5.0503)
  - -10% (4.5453): Sharpe = 0.16
  - +10% (5.5553): Sharpe = 0.16
- **max_hold_bars** (Baseline: 181)
  - -10% (163): Sharpe = 0.16
  - +10% (199): Sharpe = 0.16

*Stability Assessment*: The strategy displays extreme sensitivity to changes in the Bollinger Band period and standard deviation parameters. A simple 10% change in `bb_period` (to 39 or 47) crashes the Sharpe ratio to -0.46 and -0.75 respectively. Changing `bb_std` to 1.5635 also crashes the Sharpe to -0.68. This indicates that the strategy performance resides on a very narrow and fragile parameter peak, suggesting a high risk of overfitting.

### Cross-Asset Stress Test
We ran the strategy with the same parameters on secondary assets (using the 4h timeframe):
- **ETH**: Sharpe = -1.41, Trades = 113, Total Return = -54.84%
- **BTC (Primary)**: Sharpe = 0.16, Trades = 104, Total Return = 3.97%

*Cross-Asset Assessment*: The strategy fails the cross-asset stress test. Performance is extremely poor on ETH (Sharpe of -1.41 and a loss of -54.84%), showing that the volatility squeeze parameters optimized for BTC are completely invalid for other assets and lack general market applicability.

---

## 3. Expert Commentary

### Trade Character
With 104 trades over a 3-year period on the 4h timeframe (approx. 1 trade every 10 days), the strategy has a moderate trade frequency. However, a win rate of 27.88% is exceptionally low, meaning the strategy relies on rare large wins to stay positive. The Profit Factor of 1.06 is extremely thin, offering almost no buffer against transaction costs and slippage in live trading.

### Chop Warnings
The combination of a low win rate (27.88%) and high parameter sensitivity suggests the strategy is prone to severe whipsawing in choppy regimes. When the Bollinger Band/Keltner Channel squeeze is triggered, many entries result in false breakouts or late entries on brief volatility spikes that quickly reverse. In the absence of a robust trend filter or volume confirmations, the strategy frequently buys local tops or sells local bottoms.

### Hypothesis Alignment
The original alpha hypothesis predicted that combining a Bollinger Band / Keltner Channel squeeze with a low ADX filter (`adx < 25`) would capture high-momentum trend expansions from a consolidated base. However, the backtest results show that while the squeeze does filter entries, the Fisher Transform trigger is highly prone to noise on the 4h timeframe. Additionally, the lack of performance on ETH indicates that the volatility characteristics required by the current parameters are highly asset-specific and do not represent a robust, generalizable volatility breakout anomaly.
