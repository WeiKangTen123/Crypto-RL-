---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: dmi-adx-trend-strength
source: TradingView / 2026 Trend Analysis
status: REJECTED
tags:
- rejected
timeframes: 1h, 4h
type: long-term
---
# DMI ADX Trend Strength

## Rejection Notes
- Sharpe Ratio: -0.48
- Total Return: -26.70%
- Win Rate: 25.81% (8/31 trades)
- Observations: The strategy suffered in choppy or mean-reverting phases. While ADX > 25 is a standard trend filter, it often resulted in late entries and early exits during the 2023 BTC test period, leading to a negative Sharpe and significant drawdown.

## Concept
This strategy identifies strong trending environments using the Directional Movement Index (DMI). It enters when a positive/negative DI crossover occurs, provided the Average Directional Index (ADX) is above a threshold, indicating a strong trend is present.

## Entry Conditions
- Long: DI+ crosses above DI- AND ADX > 25
- Short: DI- crosses above DI+ AND ADX > 25

## Exit Conditions
- Take profit: ATR-based trailing stop (2.5 * ATR) or DI cross back
- Stop loss: 1.5 * ATR from entry price

## Key Indicators
- DMI (14)
- ADX (14)
- ATR (14) for risk management

## Expected Edge
Crypto markets tend to trend strongly once a move is established. ADX filters out the "noise" of low-volatility ranging periods, while DMI provides the direction.

## Data Requirements
- Columns needed: High, Low, Close
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- ADX threshold might need optimization per coin (e.g., SOL might need higher ADX than BTC).

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]] · [[Trend_Momentum/20260527_ema_ribbon_rsi_momentum]]
