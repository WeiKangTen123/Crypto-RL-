---coins: ETH
interest: ACTIVE
name: forge129_mtf_ema_cross
source: strategy_forge
strategy_id: FORGE_ETH_MTF_EMA_CROSS
status: VALIDATED
tags:
- MTF
- EMA
- trend-following
- taker
- 1h
- 4h-filter
timeframes:
- 1h
- 4h
type: Trend_Momentum
sharpe: 1.12
win_rate: 33.59
total_return: 153.06
max_drawdown: 21.99
---

# MTF EMA Cross — 1h Entry / 4h Trend Filter

## Concept
Multi-timeframe trend-following: entry signals generated on 1h, validated against 4h structural trend and real-time order flow. First forge strategy to use the htf_ema_trend filter infrastructure.

## Entry Signal
EMA(8) crosses above EMA(21) on 1h data.

## Filters
1. **htf_ema_trend** (htf_bars=4, htf_ema_period=50): 4h price must be above 4h EMA(50) — only enter in confirmed 4h uptrend
2. **taker_confirm** (intensity_period=13): taker buy ratio > 0.5 — active buying pressure at entry

## Exit
`atr_tp_sl_hold`: TP = 10×ATR(14), SL = 3×ATR(14), max hold = 96 bars (4 days)

## Expected Edge
- Higher timeframe context eliminates most counter-trend 1h signals
- Taker confirm ensures institutional follow-through
- Large TP/SL ratio (3.3:1) absorbs 1h fee drag at 10× leverage

## Implementation Notes
- Strategy #129 in STRATEGY_LIBRARY
- Requires ETH/1h data with DatetimeIndex (resample uses `4h` rule internally)
- Deployed at r=0.06, l=10 → ~2.85%/month, ~22% MDD
- Trade frequency: ~1.1/week (3-7/week target unachievable with acceptable Sharpe on ETH)


## Performance Summary
*Auto-updated by sync_backtest_to_obsidian.py when strategy_id matches.*

| Metric | Value |
| --- | --- |
| Sharpe Ratio | 1.12 |
| Win Rate | 33.59% |
| Total Return | 153.06% |
| Max Drawdown | 21.99% |