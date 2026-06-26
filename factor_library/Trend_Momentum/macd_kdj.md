---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: macd-kdj
source: 量化验证室 EP15
status: IMPLEMENTED
tags:
- implemented
timeframes: 1h
type: short-term
---
# MACD KDJ Strategy

## Concept
Entry requires two conditions to both occur within a rolling `entry_window` of bars — KDJ cross at extreme zone AND MACD histogram flip. Exit is driven by KDJ opposite cross rather than a fixed target. EMA(200) trend filter blocks counter-trend trades.

## Entry Conditions
**Long:**
- K < oversold threshold (30) AND KDJ golden cross within window
- MACD histogram flips from negative → positive within same window
- Price above EMA(200)

**Short:**
- K > overbought threshold (70) AND KDJ death cross within window
- MACD histogram flips from positive → negative within same window
- Price below EMA(200)

Only the rising edge of the condition fires — prevents repeated entries during the same window.

## Exit Conditions
- KDJ opposite cross (primary exit signal)
- Price-based stop loss: 9.05% from entry (intrabar)
- Max hold: 36 bars force-close

## Key Indicators
- MACD(12, 26, 9) — histogram sign-flip trigger
- KDJ(9) — K/D crossover at extreme zones
- EMA(200) — trend direction filter
- Entry window: 5 bars

## Expected Edge
Combines momentum exhaustion (KDJ extreme) with trend-change confirmation (MACD flip) — both must agree within a short window to reduce false entries. EMA filter removes counter-trend noise.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Uses rolling window logic — both conditions don't need to fire on the same bar
- Rising-edge detection prevents multi-bar repeated entries

## Implementation Status: IMPLEMENTED

## Strategy Class
`MACDKDJStrategy` — `strategy_backtest/strategies/macd_kdj_strategy.py`

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
