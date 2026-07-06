---
status: MEDIOCRE
id: 53
sharpe: 0.69
return: 55.0
mdd: 12.7
win_rate: 34.8
trades: 54
pf: 1.80
---
# Stage 03 Backtest Report: WaveTrendMFIDivergenceStrategy

## Performance Table

| Metric | Baseline (Pre-Tuning) | Post-Tuning (Validation Engine) | Post-Tuning (Best Optuna Trial) |
| :--- | :---: | :---: | :---: |
| **Sharpe Ratio** | 0.36 | **0.690** | **0.810** |
| **Total Return** | 8.2% | **55.0%** | **67.7%** |
| **Max Drawdown** | 8.2% | **12.7%** | **12.4%** |
| **Win Rate** | 62.5% | **34.8%** | **34.8%** |
| **Total Trades** | 8 | **54** | **46** |
| **Profit Factor** | 2.01 | **1.80** | **1.80** |

## Stability & Robustness

### 1. Parameter Stability Test (FAILED)
A systematic $\pm10\%$ perturbation was applied to all numerical strategy parameters:
*   **Fast WaveTrend Length (`wt_n1`)**: Very fragile. Increasing `wt_n1` from 5 to 6 crashed the Sharpe Ratio from **0.690** to **0.200** (a $71\%$ drop). Decreasing to 4 improved Sharpe to 0.760.
*   **Money Flow Index Period (`mfi_period`)**: Highly sensitive. Decreasing `mfi_period` from 16 to 14 crashed the Sharpe to **0.180** ($74\%$ drop). Increasing to 18 dropped Sharpe to **0.340** ($51\%$ drop).
*   **Other Parameters**: Parameters such as `wt_n2` (11), `wt_oversold` (-10), `wt_overbought` (76), `ema_period` (26), and risk parameters (`tp_rr` and `sl_atr_mult`) proved stable.
*   *Audit Verdict*: The strategy parameters display high sensitivity around the fast oscillator channel (`wt_n1`) and volume gating (`mfi_period`). Because perturbations of these parameters cause the Sharpe Ratio to drop below the $0.3$ threshold, the strategy is flagged as **MEDIOCRE** due to parameter fragility.

### 2. Cross-Asset Stress Test (PASSED)
The optimized parameter set was verified across secondary assets on the same $1\text{h}$ timeframe:
*   **ETH/1H**: Sharpe **0.580** | 47 Trades | Return **34.6%** | Max Drawdown 12.7%
*   **BTC/1H**: Sharpe **0.690** | 60 Trades | Return **41.2%** | Max Drawdown 12.7%
*   *Audit Verdict*: The momentum-volume divergence logic carries global market validity. Profitability is replicated successfully on both ETH and BTC without modification, confirming a solid underlying alpha factor.

## Expert Commentary

### Trade Character
WaveTrendMFIDivergenceStrategy captures exhaustion points by identifying divergences between price actions and the WaveTrend indicator, gated by Money Flow index and trend alignment.
Post-tuning, the strategy shifted from a high-win-rate, low-frequency setup (Win Rate 62.5%, 8 trades) to a breakout/trend-following divergence setup (Win Rate 34.8%, 54 trades). The profitability is driven by the wide risk-to-reward ratio (`tp_rr = 4.2167`), which allows a small number of winning trades to easily cover the small ATR-stopped losses.

### Chop Warnings
Because the EMA filter is set relatively short (`ema_period = 26`), the strategy is prone to whipsawing during extended sideways consolidations (chop). In range-bound regimes, false divergences will generate consecutive losses, although the wide target ratio ensures drawdown remains controlled.

### Hypothesis Alignment
The core hypothesis—that combining momentum exhaustion (WaveTrend) with volume flow exhaustions (MFI) yields reliable reversion entries—is supported by the backtest results. However, the extreme parameter fragility suggests the divergence signal's timing is highly sensitive. The fast oscillator period must be exactly calibrated to avoid lag, making it a mediocre candidate for live deployment without dynamic parameter tracking.
