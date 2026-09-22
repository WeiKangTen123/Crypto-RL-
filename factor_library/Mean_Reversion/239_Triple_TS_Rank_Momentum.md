---
name: Strategy_256
strategy_id: 256
type: factor
directional_bias: Symmetric
optimal_regime: Trending, Low-Chop
timeframes: 1h, 4h
coins: BTC
status: REJECTED
sharpe: -10.0
win_rate: 0.0
total_return: 0.0
max_drawdown: 0.0
tags: [factor_card, Phase4_DeepTuned, Strategy_256, REJECTED]
---

# Alpha Card: Strategy #256 - Triple TS Rank Momentum

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#256** |
| **Status** | **REJECTED** |
| **Sharpe Ratio** | **-10.0** |
| **Total ROI** | **0.0%** |
| **CAGR** | **0.0%** |
| **Max Drawdown** | **0.0%** |
| **Win Rate** | **0.0%** |
| **Profit Factor** | **0.0** |
| **Total Trades** | **2066** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 11,
  "p2": 72,
  "threshold": 0.9,
  "regime_gate": "ema200",
  "use_adx": false,
  "sl_atr": 2.5,
  "tp_atr": 7.0,
  "max_hold": 26
}
```
