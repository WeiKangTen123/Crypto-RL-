---
name: Strategy_254
strategy_id: 254
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
tags: [factor_card, Phase4_DeepTuned, Strategy_254, REJECTED]
---

# Alpha Card: Strategy #254 - Hurst Regime Adaptive

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#254** |
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
  "p1": 9,
  "p2": 30,
  "threshold": 0.45,
  "regime_gate": "ema50",
  "use_adx": false,
  "sl_atr": 4.5,
  "tp_atr": 4.0,
  "max_hold": 65
}
```
