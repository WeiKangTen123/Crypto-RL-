---
coins: SOL, BNB
interest: High
name: dynamic-vwap-atr-scalper
source: Web (Meme scalping logic adaptation)
status: IMPLEMENTED
tags:
- queued
timeframes: 5m, 15m, 1h
type: short-term
---
# Dynamic VWAP ATR Scalper

## Concept
A strategy designed to scalp high-volatility assets by trading mean-reversion around the VWAP, using dynamic ATR-based bands to identify overextended price levels.

## Entry Conditions
- Price deviates significantly from the VWAP (e.g., > 2x ATR).
- RSI (or similar momentum oscillator) indicates extreme oversold/overbought conditions.
- Volume spikes confirm exhaustion.
- Entry is a fade (counter-trend) back toward the VWAP.

## Exit Conditions
- Take profit: Partial at VWAP, remainder trailed.
- Stop loss: Hard stop at 1.5x ATR beyond the entry point to prevent catching a falling knife.

## Key Indicators
- VWAP
- ATR (14)
- RSI (14)
- Volume

## Expected Edge
In highly volatile markets (like SOL or meme tokens), sharp deviations from the mean (VWAP) often result in snap-backs as aggressive takers exhaust their liquidity and market makers re-center the price.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 5m, 15m, 1h
- Minimum history: 1 year

## Implementation Notes
- Needs tick-level or very granular data to calculate accurate intra-day VWAP if running live, but for backtesting, standard OHLCV VWAP approximations might suffice.
- Strict stop-losses are critical.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Volatility_Breakout/20260527_bbw_volatility_breakout]]
