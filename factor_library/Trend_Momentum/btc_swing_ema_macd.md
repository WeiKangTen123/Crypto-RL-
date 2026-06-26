---
coins: BTC
interest: High
name: btc-swing-ema-macd
source: StratBase.ai metadata
status: IMPLEMENTED
tags:
- implemented
timeframes: 4h
type: long-term
---
# BTC Swing EMA MACD

## Concept
Swing trading strategy for BTC on the 4H timeframe. Uses EMA as a trend filter, RSI as a momentum gate, and MACD golden cross as the entry trigger. Long-only bias — no short entries.

## Entry Conditions
- Price must be above EMA(20) — trend filter
- RSI(14) > 50 — bullish momentum
- MACD line crosses above Signal line (golden cross) on the same bar

## Exit Conditions
- Take profit: 8% fixed from entry price
- Stop loss: 3% fixed from entry price (intrabar check on Low)

## Key Indicators
- EMA(20) — trend direction filter
- RSI(14) — momentum gate (threshold: 50)
- MACD(12, 26, 9) — entry trigger on golden cross

## Expected Edge
Clean trend-following setup on 4H — filters out noise with RSI and EMA before entering on MACD confirmation. Asymmetric TP/SL (8%/3%) gives favorable R:R on trending moves.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Long-only — no short signal logic
- TP/SL checked intrabar (High/Low), not on close

## Implementation Status: IMPLEMENTED

## Strategy Class
`BTCSwingEMAMACD` — `strategy_backtest/strategies/btc_swing_ema_macd_strategy.py`

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Trend_Momentum/20260527_supertrend_pro]] · [[Trend_Momentum/20260526_supertrend_pro_volatility]] · [[Trend_Momentum/20260526_supertrend_atr_momentum]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]] · [[Volatility_Breakout/trend_following_donchian_channel_breakout_impl]] · [[Volatility_Breakout/20260527_avso_momentum]]
