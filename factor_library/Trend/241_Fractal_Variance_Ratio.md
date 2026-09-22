---
name: Strategy_247
strategy_id: 247
type: factor
directional_bias: Symmetric
optimal_regime: Trending, Low-Chop
timeframes: 1h, 4h
coins: BTC
status: MEDIOCRE
sharpe: 0.13
win_rate: 20.0
total_return: 1.11
max_drawdown: 4.13
tags: [factor_card, Phase4_DeepTuned, Strategy_247, MEDIOCRE]
---

# Alpha Card: Strategy #247 - Fractal Variance Ratio

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#247** |
| **Status** | **MEDIOCRE** |
| **Sharpe Ratio** | **0.13** |
| **Total ROI** | **1.11%** |
| **CAGR** | **0.2%** |
| **Max Drawdown** | **4.13%** |
| **Win Rate** | **20.0%** |
| **Profit Factor** | **1.07** |
| **Total Trades** | **60** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 18,
  "p2": 70,
  "threshold": 0.9,
  "regime_gate": "none",
  "use_adx": true,
  "sl_atr": 1.5,
  "tp_atr": 3.0,
  "max_hold": 26
}
```
