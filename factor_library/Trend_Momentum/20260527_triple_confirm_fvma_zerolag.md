---
coins: BTC, ETH, SOL
interest: High
name: triple_confirm_fvma_zerolag
source: Web Search (TradingView 2026)
status: COMPLETED
tags:
- built
- backtested
- REJECTED
timeframes: 1h, 4h
type: short-term
---
# Triple Confirmation FVMA ZeroLag MACD

## Concept
A hybrid strategy combining Supertrend for overall direction, Fair Value Moving Average (FVMA) for trend strength, and Zero Lag MACD for entry timing. This triple-confirmation approach reduces false signals in volatile crypto markets.

## Entry Conditions
- Supertrend must indicate an uptrend (price > Supertrend line).
- Close price must be above the FVMA, indicating trend strength.
- Zero Lag MACD line crosses above the signal line.

## Exit Conditions
- Take profit: 3x ATR target or trailing stop.
- Stop loss: Below recent swing low or Supertrend line.
- Exit on Zero Lag MACD cross down.

## Key Indicators
- Supertrend (10, 3)
- FVMA (Fair Value Moving Average) / EMA (if FVMA not available)
- Zero Lag MACD (12, 26, 9)

## Expected Edge
Reduces the inherent lag of standard MACD while using structural trend support (Supertrend) to filter out chop.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Will use EMA if FVMA calculation is complex.
- Requires calculating Zero Lag MACD (ZMACD = MACD + (MACD - MACD[1])).

## Rejection Notes
- Tested on BTC 1h data (2023-2024).
- The highest Sharpe Ratio achieved during hyperparameter optimization (Supertrend, FVMA, ATR TP/SL) was -1.25.
- The combination of Supertrend, EMA (FVMA), and ZMACD crossover filters out too many good trades and enters late, resulting in a negative edge in the crypto market.
- Discarded.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260528_zero_lag_trend_speed_momentum]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]]
