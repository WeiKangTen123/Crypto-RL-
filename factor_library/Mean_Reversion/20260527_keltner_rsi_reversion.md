---
coins: BTC, ETH, SOL
interest: High
name: keltner-rsi-reversion
source: Web Research
status: COMPLETED
tags:
- built
- backtested
- REJECTED
timeframes: 1h, 4h
type: short-term
---
# Keltner RSI Reversion

## Concept
Mean reversion strategy that combines Keltner Channels (KC) and the Relative Strength Index (RSI). Keltner channels use Average True Range (ATR) to set bands around a moving average. When price breaks outside the Keltner Channel and RSI is simultaneously in overbought/oversold territory, it signals an overextended move likely to revert to the mean.

## Entry Conditions
- **Long**:
    1. Close is below the Lower Keltner Channel.
    2. RSI is below oversold threshold (e.g., < 30).
- **Short**:
    1. Close is above the Upper Keltner Channel.
    2. RSI is above overbought threshold (e.g., > 70).

## Exit Conditions
- **Take Profit**: Price touches the Keltner Channel Middle Band (EMA) or opposite band.
- **Stop Loss**: Fixed percentage or ATR multiplier away from entry.

## Key Indicators
- **Keltner Channels**: EMA (typically 20), ATR (typically 10), Multiplier (typically 2.0).
- **RSI**: Period 14.

## Expected Edge
Provides high-probability mean reversion setups in ranging markets by requiring both price extreme (KC) and momentum exhaustion (RSI).

## Data Requirements
- Columns needed: Close, High, Low.
- Minimum timeframe: 1h
- Minimum history: 1 year

## Rejection Notes
- **Date**: 2026-05-27
- **Reason**: Sharpe Ratio -3.58 on BTC 1H (2023-2024). High frequency of losing trades in trending markets. The strategy failed to handle the 2023 bull run, consistently trying to short the top or buy local bottoms that weren't bottoms.


---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Mean_Reversion/20260527_aroon_rsi_mean_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]]
