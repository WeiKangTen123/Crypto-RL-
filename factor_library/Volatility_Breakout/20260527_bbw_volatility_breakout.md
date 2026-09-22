---
coins: BTC, SOL, BNB
interest: High
name: bbw_volatility_breakout
source: GitHub (Quantitative breakout strategies)
status: IN_PROGRESS
tags:
- built
- backtested
- in_progress
timeframes: 15m, 1h
type: short-term
---
# Bollinger Band Width Volatility Breakout

## Concept
Markets alternate between periods of low volatility (consolidation) and high volatility (expansion). This strategy detects extreme low volatility using Bollinger Band Width (BBW) and trades the subsequent explosive breakout when price closes outside the Bollinger Bands.

## Entry Conditions
- Volatility Squeeze: BBW is lower than its own N-period moving average (or in the bottom X percentile of its lookback).
- Breakout Long: Current Close is greater than the Upper Bollinger Band.
- Breakout Short: Current Close is less than the Lower Bollinger Band.
- Volume Confirmation: Current volume is greater than the volume SMA.

## Exit Conditions
- Take profit: Trailing stop or when price crosses back the Bollinger Middle Band (SMA).
- Stop loss: Fixed percentage (e.g., 2-3%) or previous candle's opposite extreme.

## Key Indicators
- Bollinger Bands (typically 20, 2).
- Bollinger Band Width (Upper Band - Lower Band) / Middle Band.
- Volume SMA.

## Expected Edge
Crypto assets, especially volatile ones like SOL and BNB, exhibit strong momentum post-consolidation. Entering early on the volatility expansion captures the "meat" of the move.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume.
- Minimum timeframe: 15m
- Minimum history: 2 years

## Implementation Notes
- Ensure the squeeze condition is strictly defined to avoid false breakouts.
- The momentum entry must happen immediately as the band is breached.
\n## Rejection Notes\nFailed Walk-Forward Validation (WFO). Passed only 2 out of 4 windows for Sharpe > 0.5 (Window 1: 3.41, Window 2: -0.55, Window 3: 0.34, Window 4: 2.67). Discarded.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/Bollinger_Bands]]

**Related Factors:** [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]]
