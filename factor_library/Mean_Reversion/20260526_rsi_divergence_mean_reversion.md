---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: rsi-divergence-mean-reversion
source: TradingView / GitHub (fmzquant)
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: short-term
---
# RSI Divergence Mean Reversion

## Concept
Identifies when price momentum is fading (RSI divergence) even as price hits a new high or low within a range. This exploits the tendency of price to revert to its mean when momentum exhausts.

## Entry Conditions
- **Bullish Divergence (Buy):** Price makes a Lower Low, but RSI (14) makes a Higher Low.
- **Bearish Divergence (Sell):** Price makes a Higher High, but RSI (14) makes a Lower High.
- **Filter:** ADX (14) < 25 to ensure we are in a ranging market.

## Exit Conditions
- Take profit: Opposite RSI extremity (e.g., if Long, TP when RSI > 70) or Middle Bollinger Band.
- Stop loss: Recent swing low/high or 1.5x ATR.

## Key Indicators
- RSI (14)
- ADX (14)
- Bollinger Bands (20, 2)

## Expected Edge
Momentum exhaustion often precedes a reversal in sideways markets. Divergence is a high-probability signal for these reversals.

## Data Requirements
- Columns needed: close, high, low, volume
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Requires a peak/trough detection logic for divergence.
- Needs to handle "fakeouts" where divergence happens but price continues to trend (ADX filter helps here).

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/Bollinger_Bands]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]]
