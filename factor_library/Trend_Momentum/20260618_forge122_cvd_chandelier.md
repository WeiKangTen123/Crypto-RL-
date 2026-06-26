---
coins:
- ETH
interest: High
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- cvd
- order_flow
- chandelier
- trailing_stop
- implemented
timeframes:
- 4h
type: order-flow
---
# FORGE #122 — CVD Cross + Chandelier TP

## Concept
Cumulative Volume Delta (CVD) crossover identifies shifts in order flow dominance (from sell-side to buy-side pressure). Chandelier exit provides an ATR-based trailing stop from the highest high, capturing the bulk of upside while managing reversal risk.

## Entry Conditions
- CVD crosses from negative to positive (buy pressure takes over)

## Filter Conditions
- None

## Exit Conditions
- Chandelier TP: trailing stop based on highest high minus ATR multiplier, plus ATR take profit

## Key Indicators
- CVD (cumulative delta of taker buys minus sells)
- Chandelier Exit (ATR trailing from peak)

## Expected Edge
CVD shifts are leading indicators of price moves — institutional accumulation shows in delta before price responds. Chandelier exit efficiently captures trend gains while tightening stop as peak extends.

## Data Requirements
- Columns needed: Close, High, Low, taker_buy_volume, volume
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 122
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.22

---
## Connections

**Category:** [[Trend_Momentum/_Index]]


**Related Factors:** [[Trend_Momentum/20260618_forge125_fvg_taker_wr_atr]]
