---
name: Strategy_250
strategy_id: 250
type: factor
directional_bias: Symmetric
optimal_regime: Trending, Low-Chop
timeframes: 1h, 4h
coins: BTC
status: VALIDATED
sharpe: 0.86
win_rate: 19.64
total_return: 8.24
max_drawdown: 2.79
tags: [factor_card, Phase4_DeepTuned, Strategy_250, VALIDATED]
---

# Alpha Card: Strategy #250 - Rank Decay Cascade

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#250** |
| **Status** | **VALIDATED** |
| **Sharpe Ratio** | **0.86** |
| **Total ROI** | **8.24%** |
| **CAGR** | **1.46%** |
| **Max Drawdown** | **2.79%** |
| **Win Rate** | **19.64%** |
| **Profit Factor** | **1.95** |
| **Total Trades** | **56** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 10,
  "p2": 67,
  "threshold": 0.65,
  "regime_gate": "ema200",
  "use_adx": true,
  "sl_atr": 3.0,
  "tp_atr": 8.0,
  "max_hold": 35
}
```
