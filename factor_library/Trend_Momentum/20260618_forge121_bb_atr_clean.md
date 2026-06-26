---
coins:
- ETH
interest: Medium
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- bollinger_band
- atr
- breakout
- implemented
timeframes:
- 4h
type: volatility-breakout
---
# FORGE #121 — BB Breakout + ATR Exit (Clean)

## Concept
Minimal-filter Bollinger Band breakout strategy with ATR TP/SL exits. No trend filter adds to trade frequency, while ATR-scaled exits adapt to volatility. Cleaner version of #118 without the EMA macro filter.

## Entry Conditions
- Close breaks above Bollinger Band upper band (bb_breakout)

## Filter Conditions
- None

## Exit Conditions
- ATR TP/SL: fixed ratio ATR take profit and stop loss

## Key Indicators
- Bollinger Bands
- ATR

## Expected Edge
Unfiltered BB breakouts capture more trades at the cost of some false signals; ATR exits manage each trade's risk autonomously.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 121
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.31

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/20260618_forge118_bb_breakout_ema_atr]]
