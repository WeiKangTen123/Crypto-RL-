---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: taker-buy-intensity-momentum
source: Quant Research / Order Flow
status: IMPLEMENTED
tags:
- queued
- implemented
timeframes: 1h, 4h
type: short-term
---
# Taker Buy Intensity Momentum

## Concept
Leverages the `taker_buy_base_vol` metric to identify periods of aggressive market buying. When takers are willing to buy at the ask aggressively, it signals high conviction and potential trend continuation or breakout.

## Entry Conditions
- Long:
    1. Taker Buy Ratio (Taker Buy Vol / Total Vol) > 0.55.
    2. Volume > 20-period SMA of Volume.
    3. Close > 20-period EMA of Close.
- Short:
    1. Taker Buy Ratio < 0.45 (meaning Taker Sell Ratio > 0.55).
    2. Volume > 20-period SMA of Volume.
    3. Close < 20-period EMA of Close.

## Exit Conditions
- Take profit: ATR-based (3 * ATR) or Taker Buy Ratio reverts to neutral (0.50).
- Stop loss: ATR-based (1.5 * ATR).

## Key Indicators
- Taker Buy Ratio (Custom)
- Volume SMA (20)
- EMA (20)
- ATR (14)

## Expected Edge
Order flow precedes price. Aggressive takers (market orders) are the "movers" of the market. Identifying their concentration provides a leading signal for momentum.

## Data Requirements
- Columns needed: Close, Volume, taker_buy_base_vol
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Ensure `taker_buy_base_vol` is correctly cast to numeric.
- Ratio threshold (0.55) should be optimized.

## Rejection Notes
Quick backtest (2023-01-01 to 2024-01-01) resulted in a Sharpe Ratio of -5.25 and -89.5% return. The neutral ratio exit (0.50) likely caused excessive churn (490 trades) and death by fees. Discarded.


---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/Order_Flow]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
