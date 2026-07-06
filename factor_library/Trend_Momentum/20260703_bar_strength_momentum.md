---
name: bar-strength-momentum
strategy_id: 190
type: momentum
factor_class: Trend_Momentum
directional_bias: Symmetric
optimal_regime: Trending
timeframes: 4h, 1h
coins: BTC, ETH, SOL
source: WorldQuant 101 Formulaic Alphas — Alpha#53 (Kakushadze 2015)
interest: High
status: COMPLETED
sharpe: 0.44
win_rate: 31.50
total_return: 65.15
max_drawdown: 39.03
tags: [built, backtested, finetuned, MEDIOCRE, alpha53, bar-strength, momentum]
---
# Bar Strength Momentum

## Concept
Adapted from WorldQuant Alpha#53. Bar Strength measures where the close falls within the bar's High-Low range:
```
bar_strength = (2*close - high - low) / (high - low)   # -1 to +1
```
+1 = close at high (fully bullish bar), -1 = close at low (fully bearish bar).
The N-bar delta of bar_strength captures intrabar momentum shifts:
```
bs_delta = bar_strength - bar_strength.shift(N)
```
Positive bs_delta = bars closing progressively higher within range → momentum entry.

## Entry Logic
- Long: bs_delta > threshold AND ADX > adx_threshold
- Short: bs_delta < -threshold AND ADX > adx_threshold

## Exit Logic
- ATR trailing stop (3×) + initial SL (2×)

## Performance (BTC/4H, 2021-2026, initial params)
| Metric | Value |
|--------|-------|
| Sharpe | -2.67 |
| ROI | -99.47% |
| MDD | 99.59% |
| Trades | 795 |

## Failure Analysis
- bs_period=9 and threshold=0.3 generates 795 trades on BTC 4H (too many)
- ADX(25) insufficient as gate; needs higher threshold (30-40)
- Bar strength delta of 0.3 on 4H is easily achieved, especially intraday

## Connections
**Category:** [[Trend_Momentum/_Index]]
**Source Paper:** `report/101 Formulaic Alphas.pdf` Alpha#53
**Related:** [[Trend_Momentum/20260703_price_momentum_acceleration]] · [[Volatility_Breakout/20260526_diamond_triangle_breakout]]
