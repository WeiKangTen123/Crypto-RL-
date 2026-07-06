---
name: price-momentum-acceleration
strategy_id: 189
type: mean-reversion
factor_class: Trend_Momentum
directional_bias: Symmetric
optimal_regime: Any
timeframes: 1h, 4h
coins: ETH, BTC, SOL
source: WorldQuant 101 Formulaic Alphas — Alpha#46 (Kakushadze 2015)
interest: High
status: COMPLETED
sharpe: 0.75
win_rate: 38.32
total_return: 232.96
max_drawdown: 34.38
tags: [built, backtested, finetuned, MEDIOCRE, alpha46, momentum-acceleration, mean-reversion]
---
# Price Momentum Acceleration

## Concept
Adapted from WorldQuant Alpha#46. Computes the 2nd-order price difference (acceleration of momentum):
```
accel_pct = (close + delay(close, slow) - 2 * delay(close, fast)) / close
```
This is proportional to the second derivative of price — positive when recent momentum has exceeded prior momentum. Normalised via rolling z-score to fade extremes (contrarian mean-reversion on momentum exhaustion).

## Entry Logic
- Long: z-score < -threshold (price was decelerating sharply downward)
- Short: z-score > +threshold (price was accelerating sharply upward)

## Exit Logic
- ATR trailing stop (3×) + initial SL (2×)

## Performance (ETH/1H, 2021-2026, initial params)
| Metric | Value |
|--------|-------|
| Sharpe | -4.05 |
| ROI | -100% |
| MDD | 100% |
| Trades | 2038 |

## Failure Analysis
- Entry threshold (1.5 sigma) fires ~15% of bars → 2038 trades on ETH 1H over 5.5yr
- Fee destruction: $0.05% × 2 sides × 2038 trades rapidly compounds losses
- Needs finetune to raise threshold to 2.5+ sigma and extend periods

## Connections
**Category:** [[Trend_Momentum/_Index]]
**Source Paper:** `report/101 Formulaic Alphas.pdf` Alpha#46
**Related:** [[Trend_Momentum/20260703_bar_strength_momentum]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]]
