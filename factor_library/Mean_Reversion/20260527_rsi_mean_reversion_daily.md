---
coins: BTC, ETH
interest: High
name: rsi-mean-reversion-daily
source: Reddit / Pine Script 2024 Strategies
status: QUEUED
tags:
- queued
timeframes: 1d
type: long-term
---
# RSI-Based Mean Reversion (Daily)

## Concept
A simple but effective mean reversion strategy for the daily timeframe that has historically outperformed Bitcoin "Buy and Hold" in risk-adjusted terms. It uses a very fast RSI to catch short-term overbought/oversold conditions within a broader trend.

## Entry Conditions
- Long: RSI(5) crosses below 30.
- Short: RSI(5) crosses above 70.

## Exit Conditions
- Take profit: For longs, exit when RSI(5) crosses above 70. For shorts, exit when RSI(5) crosses below 30.
- Stop loss: Time-based stop (e.g., exit after 5 days if not profitable) or a wide fixed percentage stop (e.g., 10%).

## Key Indicators
- RSI with a very short period (5).

## Expected Edge
High expectancy, high reward-to-risk ratio. The win rate is typically lower (~40%), but the average win is significantly larger than the average loss.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1d
- Minimum history: 4+ years

## Implementation Notes
- It's a low-frequency strategy. 
- A trend filter (e.g., price > SMA 200) can be added to only take long trades in an uptrend, improving the win rate.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Trend_Momentum/20260527_ema_ribbon_rsi_momentum]] · [[Volatility_Breakout/20260527_avso_momentum]] · [[Trend_Momentum/20260527_supertrend_pro]] · [[Trend_Momentum/20260526_supertrend_pro_volatility]] · [[Trend_Momentum/20260526_supertrend_atr_momentum]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
