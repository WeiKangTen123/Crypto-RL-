---
name: Strategy_248
strategy_id: 248
type: factor
directional_bias: Symmetric
optimal_regime: Trending, Low-Chop
timeframes: 1h, 4h
coins: BTC
status: VALIDATED
sharpe: 0.55
win_rate: 28.36
total_return: 10.6
max_drawdown: 3.51
tags: [factor_card, Phase4_DeepTuned, Strategy_248, VALIDATED]
---

# Alpha Card: Strategy #248 - Delta Decay Fade

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#248** |
| **Status** | **VALIDATED** |
| **Sharpe Ratio** | **0.55** |
| **Total ROI** | **10.6%** |
| **CAGR** | **1.86%** |
| **Max Drawdown** | **3.51%** |
| **Win Rate** | **28.36%** |
| **Profit Factor** | **1.6** |
| **Total Trades** | **134** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 9,
  "p2": 43,
  "threshold": 0.75,
  "regime_gate": "ema50",
  "use_adx": true,
  "sl_atr": 3.0,
  "tp_atr": 7.5,
  "max_hold": 41
}
```
