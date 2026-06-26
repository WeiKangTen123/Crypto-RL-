---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: tight-bollinger-band-scalper
source: bitget.com / GitHub (benorgera)
status: QUEUED
tags:
- queued
timeframes: 15m, 1h
type: short-term
---
# Tight Bollinger Band Scalper

## Concept
Uses tightened Bollinger Bands (StdDev 1.5) to capture frequent mean-reversion moves in low-volatility ranging environments.

## Entry Conditions
- **Long:** Price closes below the Lower Bollinger Band (20, 1.5) and then closes back inside.
- **Short:** Price closes above the Upper Bollinger Band (20, 1.5) and then closes back inside.
- **Filter:** EMA 200 must be relatively flat (slope < threshold).

## Exit Conditions
- Take profit: Middle Bollinger Band (SMA 20).
- Stop loss: ATR-based (e.g., 2x ATR from entry).

## Key Indicators
- Bollinger Bands (20, 1.5)
- EMA (200)
- ATR (14)

## Expected Edge
In ranging markets, price frequently touches and reverts from 1.5 StdDev bands. Using a "close back inside" confirmation reduces being caught in a band-walk.

## Data Requirements
- Columns needed: close, high, low, volume
- Minimum timeframe: 15m
- Minimum history: 1 year

## Implementation Notes
- Very sensitive to fees; requires high-leverage and low-fee environment.
- Best on weekends or quiet sessions.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/Bollinger_Bands]] · [[_Concepts/EMA]]

**Related Factors:** [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]]
