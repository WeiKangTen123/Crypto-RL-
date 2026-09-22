---
name: Strategy_253
strategy_id: 253
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
tags: [factor_card, Phase4_DeepTuned, Strategy_253, REJECTED]
---

# Alpha Card: Strategy #253 - Fair Value Gap Recovery

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#253** |
| **Status** | **REJECTED** |
| **Sharpe Ratio** | **-10.0** |
| **Total ROI** | **0.0%** |
| **CAGR** | **0.0%** |
| **Max Drawdown** | **0.0%** |
| **Win Rate** | **0.0%** |
| **Profit Factor** | **0.0** |
| **Total Trades** | **0** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 20,
  "p2": 59,
  "threshold": 0.6000000000000001,
  "regime_gate": "ema200",
  "use_adx": true,
  "sl_atr": 2.5,
  "tp_atr": 6.5,
  "max_hold": 20
}
```
