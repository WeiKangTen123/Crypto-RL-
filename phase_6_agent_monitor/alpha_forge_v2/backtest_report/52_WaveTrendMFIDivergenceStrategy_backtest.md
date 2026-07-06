---
status: MEDIOCRE
id: 52
sharpe: 0.98
return: 93.2
mdd: 17.6
win_rate: 35.3
trades: 51
pf: 2.18
---
# Stage 03 Backtest Report: WaveTrendMFIDivergenceStrategy

## Performance Table

| Metric | Baseline (Pre-Tuning) | Post-Tuning (Validation Engine) | Post-Tuning (Best Optuna Trial) |
| :--- | :---: | :---: | :---: |
| **Sharpe Ratio** | 0.49 | **0.980** | **0.960** |
| **Total Return** | 16.1% | **93.2%** | **86.7%** |
| **Max Drawdown** | 9.5% | **17.6%** | **15.7%** |
| **Win Rate** | 42.9% | **35.3%** | **34.9%** |
| **Total Trades** | 21 | **51** | **43** |
| **Profit Factor** | 1.77 | **2.18** | **2.18** |

## Stability & Robustness

### 1. Parameter Stability Test (FAILED)
A systematic $\pm10\%$ perturbation was applied to all numerical strategy parameters:
*   **Money Flow Index Period (`mfi_period`)**: Highly sensitive. Decreasing `mfi_period` from 17 to 15 crashed the Sharpe Ratio from **0.980** to **0.460** (a $53\%$ drop).
*   **Slow WaveTrend Length (`wt_n2`)**: Sensitive. Increasing `wt_n2` from 14 to 15 crashed the Sharpe Ratio to **0.500** (a $49\%$ drop).
*   **Fast WaveTrend Length (`wt_n1`)**: Vulnerable. Increasing `wt_n1` from 12 to 13 dropped the Sharpe Ratio to **0.650** (a $34\%$ drop).
*   *Audit Verdict*: The strategy parameters display high sensitivity around the Money Flow Index gating period (`mfi_period`) and WaveTrend lengths (`wt_n1` and `wt_n2`). Because perturbations of these parameters cause the Sharpe Ratio to drop significantly, the strategy is flagged as **MEDIOCRE** due to parameter fragility.

### 2. Cross-Asset Stress Test (FAILED)
The optimized parameter set was verified across secondary assets on the same $1\text{h}$ timeframe:
*   **BTC/1H**: Sharpe **0.020** | 58 Trades | Return **-1.1%** | Max Drawdown 26.7%
*   **SOL/1H**: Sharpe **-1.010** | 60 Trades | Return **-47.1%** | Max Drawdown 53.6%
*   *Audit Verdict*: The alpha factor lacks global validity. While it generates excellent returns on ETH, it fails on both BTC and SOL, showing significant drawdown and negative or near-zero Sharpe. This indicates the optimized parameters are highly asset-specific (overfit to ETH/1H).

## Expert Commentary

### Trade Character
`WaveTrendMFIDivergenceStrategy` captures momentum exhaustion points on ETH/1H by identifying divergences between price and the WaveTrend oscillator, gated by Money Flow Index and trend alignment.
Post-tuning, the strategy increased trade frequency (from 21 to 51 trades) and achieved a much higher Sharpe (0.98 vs 0.49). Its edge is primarily driven by a wide risk-to-reward ratio (`tp_rr = 4.04`), which allows a 35.3% win rate to yield substantial returns, as the winning trades easily compensate for the small, tight stopped losses (`sl_atr_mult = 1.22`).

### Chop Warnings
Since the EMA trend filter is relatively short (`ema_period = 93`), the strategy is prone to whipsawing during extended range-bound consolidations on the 1h timeframe. During these flat regimes, false divergence signals will cluster, leading to consecutive losses. It is recommended to avoid deploying this strategy during low-volatility, ranging markets.

### Hypothesis Alignment
The core hypothesis—that momentum divergence coupled with volume flow (MFI) confirmations identifies high-probability reversion entries—is conceptually sound. However, the extreme asset-specificity (failing on BTC/SOL) and high parameter fragility (50%+ drops in Sharpe on minor indicator shifts) suggest that the current implementation is highly overfitted. It should be treated as a mediocre candidate and must be run with tight risk constraints.
