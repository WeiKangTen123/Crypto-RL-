---
name: intrabar-efficiency-momentum
strategy_id: 192
type: momentum
factor_class: Trend_Momentum
directional_bias: Symmetric
optimal_regime: Trending, low-chop
timeframes: 1h, 4h
coins: BTC, ETH
source: WorldQuant 101 Formulaic Alphas — Alpha#101 (Kakushadze 2015)
interest: High
status: COMPLETED
sharpe: 0.32
win_rate: 36.67
total_return: 19.74
max_drawdown: 16.23
tags: [built, backtested, finetuned, alpha101, intrabar-efficiency, momentum, MEDIOCRE]
---
# Intrabar Efficiency Momentum

## Concept
Adapted from WorldQuant Alpha#101. Measures directional efficiency of each bar:
```
bar_eff = (close - open) / (high - low + 1e-8)   # ∈ [-1, +1]
smooth  = rolling_mean(bar_eff, smooth_period)     # sustained efficiency
```
When smoothed efficiency is high (bars consistently bullish, close near high) AND
price is above a long EMA trend gate → momentum entry long. Symmetric for shorts.

## Entry Logic
- Long: smooth > 0.35 AND close > EMA(179)
- Short: smooth < -0.35 AND close < EMA(179)
- The EMA-179 on BTC 1H ≈ 7.5-day moving average (very selective trend gate)

## Exit Logic
- ATR trailing stop ratchet (initial 1.94×ATR SL + 3.56×ATR ratcheting trail)

## Performance (BTC/1H, 2021-2026, post-finetune)
| Metric | Value |
|--------|-------|
| Sharpe | 0.32 |
| ROI | +19.74% |
| MDD | 16.23% ← lowest in Alpha# library |
| Trades | 60 |
| Win Rate | 36.67% |
| Profit Factor | 1.36 |

## Yearly Returns
| Year | Return |
|------|--------|
| 2021 | +2.71% |
| 2022 | +2.69% |
| 2023 | +6.59% |
| 2024 | +14.43% |
| 2025 | -3.16% |
| 2026 | -3.89% |

## Key Observations
- Only 60 trades over 5.5 years → fires rarely, but when it does, edge is real
- Profit Factor 1.36 with 36.67% win rate → genuine mean-per-trade edge
- MDD 16.23% is the best capital preservation in the Alpha-series strategies
- 2025-2026 slightly negative (post-halving regime shift?)

## Connections
**Category:** [[Trend_Momentum/_Index]]
**Source Paper:** `report/101 Formulaic Alphas.pdf` Alpha#101
**Related:** [[Trend_Momentum/20260703_bar_strength_momentum]] · [[Trend_Momentum/20260703_volume_capitulation_reversal]]
