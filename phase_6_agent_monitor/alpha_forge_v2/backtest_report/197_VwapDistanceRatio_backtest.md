---
status: BAD
id: 197
sharpe: -0.03
return: -4.32
MDD: 42.15
win_rate: 34.02
trades: 541
PF: 0.94
---

# Backtest Report: 197_VwapDistanceRatio_backtest

## 1. Performance Table
| Metric | Value |
| :--- | :--- |
| **Total Return** | -4.32% |
| **Sharpe Ratio** | -0.03 |
| **Max Drawdown** | 42.15% |
| **Win Rate** | 34.02% |
| **Total Trades** | 541 |
| **Profit Factor** | 0.94 |

## 2. Stability & Robustness
- **Status**: BAD. Strategy generated negative Sharpe (-0.03) and negative expectancy out of the box.
- **Multi-Coin Execution**: Validated. The strategy successfully executed cross-margin trades across 5 assets using continuous cross-sectional VWAP ranking.
- **Parameter Sensitivity**: Untuned baseline. Defaults used a 3-bar smoothing window.

## 3. Expert Commentary
- **Trade Character**: WorldQuant Alpha #42 inherently assumes structural mean-reversion (shorting the asset furthest above VWAP, longing the one furthest below). In crypto, extreme deviation from VWAP is often trend-confirming, not mean-reverting, which explains the sub-1.0 Profit Factor.
- **Hypothesis Alignment**: The pure mean-reversion premise of this factor may require inversion for crypto, or conditional regime gating (only trade when RV ratio is low).
- **Next Steps**: Needs tuning by `crypto-strategy-tuner` to explore if inverting the signal (momentum instead of mean-reversion) yields edge.
