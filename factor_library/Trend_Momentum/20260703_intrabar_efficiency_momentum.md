---
name: Strategy_255
strategy_id: 255
type: factor
directional_bias: Symmetric
optimal_regime: Trending, Low-Chop
timeframes: 1h, 4h
coins: BTC
status: MEDIOCRE
sharpe: 0.33
win_rate: 22.97
total_return: 4.55
max_drawdown: 3.41
tags: [factor_card, Phase4_DeepTuned, Strategy_255, MEDIOCRE]
---

# Alpha Card: Strategy #255 - Intrabar Efficiency Mom.

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#255** |
| **Status** | **MEDIOCRE** |
| **Sharpe Ratio** | **0.33** |
| **Total ROI** | **4.55%** |
| **CAGR** | **0.82%** |
| **Max Drawdown** | **3.41%** |
| **Win Rate** | **22.97%** |
| **Profit Factor** | **1.26** |
| **Total Trades** | **74** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 16,
  "p2": 36,
  "threshold": 0.75,
  "regime_gate": "none",
  "use_adx": false,
  "sl_atr": 2.5,
  "tp_atr": 2.5,
  "max_hold": 23
}
```
