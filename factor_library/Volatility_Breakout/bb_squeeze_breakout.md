---
coins: BTC, ETH, BNB, SOL, XRP
interest: High
name: bb-squeeze-breakout
source: Squeeze Momentum (LazyBear) concept — TradingView
status: IMPLEMENTED
tags:
- implemented
timeframes: 1h, 4h
type: short-term
---
# Bollinger Band Squeeze Breakout Strategy

## Concept
Detects periods of volatility compression (Bollinger Bands inside Keltner Channels = squeeze) and enters when the squeeze fires and price breaks out. Momentum histogram confirms direction. Targets 3%+ monthly via high-volatility breakout captures.

## Entry Conditions
**Long:**
- Squeeze is firing (BB upper < KC upper AND BB lower > KC lower)
- Price breaks above the upper Bollinger Band
- Momentum histogram > 0 (rising)

**Short:**
- Squeeze is firing
- Price breaks below the lower Bollinger Band
- Momentum histogram < 0 (falling)

Only the rising edge fires — no repeated entries while condition holds.

## Exit Conditions
- Trailing stop: price crosses below (long) / above (short) the BB middle band (MA20) on close
- Take profit: entry ± (4.0 × ATR), checked intrabar

## Key Indicators
- Bollinger Bands(20, 2) — breakout levels and trailing stop (middle band)
- Keltner Channels(20, 1.5×ATR) — squeeze detection
- Momentum: EMA of (Close minus rolling High/Low midpoint) — direction confirmation
- ATR(20) — dynamic TP sizing

## Expected Edge
Squeeze → breakout pattern captures expansion moves after periods of compression. High-probability setup because the market has been coiling energy before the move.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Squeeze is detected by BB being fully inside KC — classic LazyBear approach
- Trailing stop uses BB mid (MA20) on close, not intrabar

## Implementation Status: IMPLEMENTED

## Strategy Class
`BB_Squeeze_Breakout_Strategy` — `strategy_backtest/strategies/bb_squeeze_breakout_strategy.py`

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/Bollinger_Bands]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]]
