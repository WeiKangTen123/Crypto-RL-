---
coins:
- ETH
interest: Medium
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- elder_ray
- bull_power
- bear_power
- chandelier
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #123 — Elder Ray + Chandelier TP

## Concept
Elder Ray Index (Bull Power = High - EMA, Bear Power = Low - EMA) entry signal triggers when bull power turns positive while price is above EMA. Chandelier exit trails the stop from peak high, letting winners run.

## Entry Conditions
- Elder Ray signal: Bull Power crosses above zero with price > EMA

## Filter Conditions
- None

## Exit Conditions
- Chandelier TP exit: trailing stop + ATR take profit

## Key Indicators
- Elder Ray Index (Bull/Bear Power)
- EMA baseline
- Chandelier Exit

## Expected Edge
Elder Ray captures the balance of power between bulls and bears relative to the EMA baseline. Bull Power > 0 signals buyers are pushing price above the mean — a high-precision momentum entry condition.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 123
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.00

---
## Connections

**Category:** [[Trend_Momentum/_Index]]


**Related Factors:** [[Trend_Momentum/20260618_forge126_btc_elder_ray_hold]]
