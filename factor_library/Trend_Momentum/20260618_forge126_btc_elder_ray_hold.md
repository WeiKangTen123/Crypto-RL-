---
coins:
- BTC
interest: Medium
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- elder_ray
- btc
- atr_expansion
- max_hold
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #126 — BTC Elder Ray + ATR Expansion + Max Hold

## Concept
Elder Ray entry on BTC (larger-cap, more mean-reverting) filtered by ATR expansion. Max hold bar exit prevents over-staying in consolidating BTC trends. Tests whether the Elder Ray edge extends to BTC's different market structure.

## Entry Conditions
- Elder Ray signal: Bull Power > 0 with price above EMA

## Filter Conditions
- ATR expansion: current ATR > vol_ma moving average

## Exit Conditions
- Max hold bars: exit after max_hold_bars=119 bars

## Key Indicators
- Elder Ray Index
- ATR expansion
- Max hold timer

## Expected Edge
BTC trends are less volatile than ETH but more sustained. Elder Ray on BTC tends to signal longer trend legs with less whipsaw, making max hold a viable exit strategy.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 3 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 126
- BTC/4h, risk 0.10, leverage 10x
- Sharpe: 1.03, ROI: 255%, MDD: 42%
- Params: period=49, adx_period=14, adx_threshold=22, atr_period=17, vol_ma_period=25, max_hold_bars=119

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/20260618_forge123_elder_ray_chandelier]]
