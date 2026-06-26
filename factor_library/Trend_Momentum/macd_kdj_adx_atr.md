---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: macd-kdj-adx-atr
source: Internal — enhanced from macd_kdj
status: IMPLEMENTED
tags:
- implemented
timeframes: 1h
type: short-term
---
# MACD KDJ ADX ATR Strategy

## Concept
Enhanced version of the MACD KDJ strategy with two additions: ADX trend strength filter (only enter when trend is strong enough) and ATR-based dynamic SL/TP (volatility-adjusted risk management instead of fixed percentages).

## Entry Conditions
**Long:**
- MACD + KDJ long signal (same as base MACD KDJ strategy)
- ADX(14) > 25 — confirms trend is strong, not ranging

**Short:**
- MACD + KDJ short signal
- ADX(14) > 25

## Exit Conditions
- ATR-based stop loss: entry ± (2.0 × ATR), checked intrabar
- ATR-based take profit: entry ± (4.0 × ATR), checked intrabar
- KDJ opposite cross
- Max hold: 72 bars force-close

## Key Indicators
- MACD(12, 26, 9) — histogram flip trigger
- KDJ(9) — cross at extreme zones
- ADX(14) — trend strength gate (threshold: 25)
- ATR(14) — dynamic SL/TP sizing (SL: 2×ATR, TP: 4×ATR)
- EMA(200) — trend direction filter

## Expected Edge
ADX filter removes false entries during sideways/choppy markets where the base MACD KDJ strategy would fire on noise. ATR-based exits scale risk with current volatility — tighter stops in low-vol, wider in high-vol.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- SL/TP set dynamically at trade entry using ATR at that bar
- Extends base MACD KDJ — shares same entry window rolling logic

## Implementation Status: IMPLEMENTED

## Strategy Class
`MACDKDJ_ADX_ATR_Strategy` — `strategy_backtest/strategies/macd_kdj_adx_atr_strategy.py`

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/20260526_dmi_adx_trend_strength]]
