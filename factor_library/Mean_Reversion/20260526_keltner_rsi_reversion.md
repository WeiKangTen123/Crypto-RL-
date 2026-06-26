---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: keltner-rsi-reversion
source: TradingView / Custom
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: short-term
---
# Keltner Channel RSI Reversion

## Concept
Identifies oversold/overbought conditions in range-bound or choppy markets using Keltner Channels for volatility bands and RSI for momentum exhaustion.

## Entry Conditions
- Long: Price closes below the lower Keltner Band (multiplier 2.0) AND RSI(14) < 30.
- Short: Price closes above the upper Keltner Band (multiplier 2.0) AND RSI(14) > 70.

## Exit Conditions
- Take profit: Price touches the Keltner Channel middle line (EMA 20).
- Stop loss: Fixed % or 1 * ATR below/above entry.

## Key Indicators
- Keltner Channels (20, 2.0, ATR 10)
- RSI (14)

## Expected Edge
Mean reversion during periods of temporary over-extension. Using Keltner Channels instead of Bollinger Bands can sometimes provide cleaner signals in crypto due to ATR-based smoothing.

## Data Requirements
- Columns needed: Open, High, Low, Close
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Simple to implement with `ta` library in Python.
- Needs to be tested against different market regimes; works best in RANGING.


## Rejection Notes
Quick backtest (2023) yielded Sharpe -3.58, Win Rate 30%, Profit Factor 0.73. Strategy discarded.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]]
