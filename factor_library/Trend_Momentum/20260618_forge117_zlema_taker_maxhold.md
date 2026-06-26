---
coins:
- ETH
interest: High
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- zlema
- taker_confirm
- max_hold
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #117 — ZLEMA Cross + Taker Confirm + Max Hold

## Concept
Zero-Lag EMA crossover (fast/slow) filtered by taker buy intensity (net taker buys as % of volume) to confirm momentum before entry. Exits are governed by a maximum hold-bar limit to prevent over-staying in decaying trends.

## Entry Conditions
- Zero-Lag EMA fast crosses above Zero-Lag EMA slow
- Net taker buy volume confirms directional pressure

## Filter Conditions
- Taker confirm: taker buy ratio above threshold at entry bar

## Exit Conditions
- Max hold bars limit (max_hold_bars=84)

## Key Indicators
- ZLEMA fast/slow crossover
- Taker buy intensity ratio

## Expected Edge
ZLEMA eliminates the lag inherent in standard EMAs, meaning crossover signals fire closer to trend inception. Taker confirm requires institutional-quality flow agreement, reducing false breakouts during low-conviction consolidations.

## Data Requirements
- Columns needed: Close, taker_buy_volume, volume
- Minimum timeframe: 4h
- Minimum history: 3 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 117
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.48, ROI: 512%, MDD: ~35%

---
## Connections

**Category:** [[Trend_Momentum/_Index]]


**Related Factors:** [[Trend_Momentum/20260618_forge125_fvg_taker_wr_atr]]
