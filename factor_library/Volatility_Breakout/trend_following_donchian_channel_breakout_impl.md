---
coins: BTC
interest: High
name: donchian-channel-breakout
source: Classic Turtle Trader system (Richard Dennis, 1983)
status: IMPLEMENTED
tags:
- implemented
timeframes: 4h
type: long-term
---
# Donchian Channel Breakout

## Concept
Classic Turtle Trader breakout system adapted for BTC 4H. Donchian Channel defines the N-bar price range (upper = highest high, lower = lowest low, middle = midpoint). Entry fires when price closes above/below the channel on confirmed volume. ADX regime filter blocks entries during ranging/choppy markets — the primary failure mode of breakout strategies.

## Entry Conditions
**Long:**
- Close > highest high of last 47 bars (new N-bar high)
- Volume > 47-bar SMA × 1.4 (volume spike confirms genuine breakout)
- ADX(29) > 27.9 (market is trending, not ranging)

**Short:**
- Close < lowest low of last 47 bars
- Same volume and ADX conditions

Rising-edge only — fires once per breakout, not on every bar while condition holds.

## Exit Conditions
- ATR Take Profit: entry ± (7.0 × ATR7) — wide target to capture trend extensions
- ATR Stop Loss: entry ∓ (0.79 × ATR7), intrabar — tight stop to cut fakeouts quickly
- Middle band exit: price closes back below/above Donchian midpoint — trend exhaustion
- Max hold: 143 bars force-close backstop

## Key Indicators
- Donchian Channel(47) — breakout level detection
- Volume SMA(47) × 1.4 — confirms genuine institutional breakout
- ADX(29) > 27.9 — regime filter, blocks entries in ranging markets
- ATR(7) — dynamic SL/TP sizing

## Expected Edge
BTC liquidation cascades create genuine multi-day breakouts when large stop clusters are triggered. ADX filter removes the 2025-style choppy periods where fakeouts dominate. Wide TP (7× ATR) lets winning trades run; tight SL (0.79× ATR) cuts losers fast.

## Data Requirements
- Columns needed: Close, High, Low, Volume
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Shift(1) on high/low before rolling — prevents look-ahead bias
- Close confirmation only — no wick-based entries (critical for BTC stop-hunting behavior)
- ADX threshold 27.9 is intentionally strict — produces few but high-quality signals

## Implementation Status: IMPLEMENTED

## Strategy Class
`DonchianBreakoutStrategy` — `strategy_backtest/strategies/donchian_breakout_strategy.py`

## Strategy ID in settings.py
`96` — `DONCHIAN_BREAKOUT_BTC_4H`

## WFO Validation Results
| Window | Sharpe | Return | MaxDD |
|---|---|---|---|
| 2023 H1 | 2.20 | +27.99% | 6.99% |
| 2024 H1 | 1.51 | +8.59% | 3.03% |
| 2025 H1 | -1.65 | -4.07% | 5.48% |
| 2026 YTD | 2.99 | +15.38% | 3.23% |

**Verdict: VALIDATED** — 3/4 windows pass (Sharpe > 0.5). 2025 H1 failed (choppy BTC market, only 2 trades).

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Volatility_Breakout/20260527_avso_momentum]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Volatility_Breakout/20260527_bbw_volatility_breakout]] · [[Volatility_Breakout/20260526_diamond_triangle_breakout]] · [[Trend_Momentum/btc_swing_ema_macd]] · [[Trend_Momentum/20260527_supertrend_pro]]
