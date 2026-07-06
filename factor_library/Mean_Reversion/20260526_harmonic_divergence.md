---
coins: BTC, ETH
interest: High
name: harmonic-divergence
source: GitHub (freqtrade-strategies) / FreqST
status: COMPLETED
tags:
- built
- backtested
timeframes: 1h, 4h
type: reversal
---
# Harmonic Divergence

## Concept
Combines harmonic patterns (like Gartley, Bat) with MACD or RSI divergences to identify high-probability trend reversals. It exploits the market's tendency to reverse at specific Fibonacci extensions when momentum diverges from price.

## Entry Conditions
- Price forms a recognized harmonic pattern (e.g., Bullish Bat).
- RSI makes a higher low while price makes a lower low (Bullish Divergence).

## Exit Conditions
- Take profit: 38.2% or 61.8% Fibonacci retracement of the pattern's AD leg.
- Stop loss: Just below the X point of the harmonic pattern.

## Key Indicators
- RSI (14)
- MACD (12, 26, 9)
- ZigZag or Peak/Trough detection for harmonic pattern recognition

## Expected Edge
Provides structured reversal entries with tight invalidation levels (tight stop losses).

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Detecting harmonic patterns programmatically can be complex; might need a simplified version focusing purely on multi-timeframe RSI divergence first.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260602_funding_rate_mean_reversion]] · [[Mean_Reversion/20260527_rsi_mean_reversion_daily]] · [[Mean_Reversion/20260527_multi_tf_rsi_divergence]] · [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Trend_Momentum/20260527_ema_ribbon_rsi_momentum]]
