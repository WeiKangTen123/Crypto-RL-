---
coins: BTC, ETH
interest: High
name: vwap-rsi-reversion
source: Web Search (TradingView mean reversion 2024)
status: COMPLETED
tags:
- built
- backtested
timeframes: 15m, 1h
type: short-term
---
# VWAP RSI Reversion

## Concept
Intraday mean reversion strategy that assumes price will snap back to the VWAP after an extreme deviation, confirmed by RSI extreme levels.

## Entry Conditions
- Price deviates from VWAP by more than a specified threshold (e.g., 2 standard deviations or a % distance).
- RSI (14) is oversold (< 30) for longs or overbought (> 70) for shorts.

## Exit Conditions
- Take profit: Price touches VWAP.
- Stop loss: Fixed % or based on a wider standard deviation band to prevent falling knife scenarios.

## Key Indicators
- VWAP
- RSI (14)

## Expected Edge
In ranging or choppy markets, crypto assets frequently revert to the intraday/weekly mean. The RSI adds a momentum exhaustion filter.

## Data Requirements
- Columns needed: High, Low, Close, Volume
- Minimum timeframe: 15m
- Minimum history: 1 year

## Implementation Notes
- Volatility filter needed: only trade if daily volatility is moderate, avoid during strong trending days (e.g., ADX > 30).
## Rejection Notes
- Tested on BTC 1H data for 2023-01-01 to 2024-01-01.
- Initial backtest yielded a Sharpe Ratio of -0.48 and Profit Factor of 0.89.
- The assumption that price snaps back to VWAP dynamically in the 1H timeframe failed to produce edge. RSI + ADX filters were insufficient to filter out strong trend days where the mean reversion fails continuously. Discarded immediately per Phase 3 rules.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260527_multi_tf_rsi_divergence]] · [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Mean_Reversion/20260527_aroon_rsi_mean_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]]
