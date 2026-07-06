---
name: volume-capitulation-reversal
strategy_id: 191
type: mean-reversion
factor_class: Trend_Momentum
directional_bias: Symmetric
optimal_regime: High-volatility, panic sell-off or exhaustion
timeframes: 4h, 1h
coins: ETH, BTC
source: WorldQuant 101 Formulaic Alphas — Alpha#43 (Kakushadze 2015)
interest: High
status: COMPLETED
sharpe: -1.04
win_rate: 19.79
total_return: -91.81
max_drawdown: 94.43
tags: [built, backtested, finetuned, alpha43, volume-capitulation, mean-reversion, BAD]
---
# Volume Capitulation Reversal

## Concept
Adapted from WorldQuant Alpha#43. Detects capitulation events using the product
of two rolling percentile ranks:
```
vol_rank     = ts_rank(volume / adv{adv_period}, rank_v_period)   # high when vol is unusually large
decline_rank = ts_rank(-delta(close, momentum_period), rank_m_period)  # high when price fell recently

buy_signal  = vol_rank × decline_rank   # high volume + declining price = panic selling
sell_signal = vol_rank × rise_rank      # high volume + rising price = euphoric exhaustion
```

Both factors are rolling percentile ranks (0-1). Their product peaks during genuine
capitulation: when volume is anomalously high AND the price has been falling. This
is a contrarian reversal signal — buy the panic, sell the euphoria.

## Entry Logic
- Long: buy_signal > threshold AND buy_signal > sell_signal
- Short: sell_signal > threshold AND sell_signal ≥ buy_signal

## Exit Logic
- ATR trailing stop ratchet (initial SL + ratcheting trail)

## Performance (ETH/4H, 2021-2026, initial params)
| Metric | Value |
|--------|-------|
| Sharpe | -3.39 |
| ROI | -99.96% |
| MDD | 99.96% |
| Trades | 1164 |

## Failure Analysis
- signal_threshold=0.35 too permissive → 1164 trades on ETH 4H
- Need threshold higher to filter only genuine capitulation events
- Finetune expected to raise threshold and tighten momentum lookback

## Connections
**Category:** [[Trend_Momentum/_Index]]
**Source Paper:** `report/101 Formulaic Alphas.pdf` Alpha#43
**Related:** [[Trend_Momentum/20260703_bar_strength_momentum]] · [[Trend_Momentum/20260703_intrabar_efficiency_momentum]]
