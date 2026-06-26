---
coins: BTC, ETH, SOL
interest: High
name: envelope-mean-reversion
source: Web / YouTube / Pine Script Community 2024
status: QUEUED
tags:
- queued
timeframes: 1h, 15m
type: short-term
---
# Envelope Mean Reversion

## Concept
This strategy focuses on identifying price extremes and betting on a return to the mean. It utilizes price envelopes (similar to Bollinger Bands or Moving Average Envelopes) to trigger entries when the price deviates significantly from the moving average. 

## Entry Conditions
- Long: Price closes below the lower envelope band.
- Short: Price closes above the upper envelope band.
- Confirmation: Volume is above average to ensure there's a strong deviation.

## Exit Conditions
- Take profit: Price returns to the central moving average (mean).
- Stop loss: Fixed percentage (e.g., 2-3%) or ATR-based stop below the entry point.

## Key Indicators
- Moving Average Envelope (e.g., SMA 20 with 2% deviation bands).
- Volume SMA for confirmation.

## Expected Edge
Crypto markets exhibit strong mean-reverting properties on intraday timeframes (15m, 1h) after sudden, sharp deviations caused by liquidations or temporary imbalances.

## Data Requirements
- Columns needed: Close, High, Low, Volume
- Minimum timeframe: 15m or 1h
- Minimum history: 2 years

## Implementation Notes
- Requires tuning the envelope deviation percentage based on the specific coin's volatility. Higher volatility coins (like SOL) need wider envelopes.

## Rejection Notes
- **Date**: 2026-05-27
- **Reason**: Fails WFO (2/4 windows passed). Excellent performance in 2023 (Sharpe 1.81) and 2024 (Sharpe 2.13), but failed in 2025 and 2026 trending markets. Mean reversion with fixed deviation is too risky in strong trends.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_aroon_rsi_mean_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]]
