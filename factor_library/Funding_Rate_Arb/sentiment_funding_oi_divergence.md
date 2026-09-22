---
name: Strategy_251
strategy_id: 251
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
tags: [factor_card, Phase4_DeepTuned, Strategy_251, REJECTED]
---

# Alpha Card: Strategy #251 - Sentiment Funding-OI Div.

## Phase 4 Deep Fine-Tuned Performance (BTC/1H, 2021-2026)
| Metric | Value |
|--------|-------|
| **Strategy ID** | **#251** |
| **Status** | **REJECTED** |
| **Sharpe Ratio** | **-10.0** |
| **Total ROI** | **0.0%** |
| **CAGR** | **0.0%** |
| **Max Drawdown** | **0.0%** |
| **Win Rate** | **0.0%** |
| **Profit Factor** | **0.0** |
| **Total Trades** | **11355** |

## Optimal Hyperparameters (Optuna TPE 80 Trials)
```json
{
  "p1": 20,
  "p2": 37,
  "threshold": 0.4,
  "regime_gate": "ema50",
  "use_adx": false,
  "sl_atr": 2.0,
  "tp_atr": 4.0,
  "max_hold": 45
}
```
