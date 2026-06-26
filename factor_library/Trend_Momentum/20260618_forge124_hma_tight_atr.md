---
coins:
- ETH
interest: High
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- hull_ma
- hma
- atr_expansion
- tight_atr
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #124 — HMA Cross + ATR Expansion + Tight ATR Exit

## Concept
Hull Moving Average (HMA) crossover for near-zero-lag trend detection, filtered by ATR expansion (confirms volatility is increasing before entry). Exits via Tight ATR (tight SL, wide TP ratio) to force only high-conviction entries to be held.

## Entry Conditions
- HMA fast crosses above HMA slow (hma_cross signal)

## Filter Conditions
- ATR expansion: current ATR > vol_ma_period ATR mean (volatility expanding)

## Exit Conditions
- Tight ATR: SL = sl_atr_mult × ATR (2.68×), TP = tp_atr_mult × ATR (6.87×), R:R ≈ 2.56

## Key Indicators
- HMA (ultra-low-lag moving average using WMA of 2×WMA(n/2) - WMA(n), smoothed by WMA(√n))
- ATR expansion filter
- Asymmetric ATR TP/SL

## Expected Edge
HMA reduces lag vs EMA/SMA allowing earlier trend entries. Tight TP/SL ratio of 2.56 forces the strategy to only hold trades with strong directional conviction, as the stop is tighter than typical.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 3 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 124
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.19, ROI: 511%, MDD: 43%
- Params: ema_fast=28, ema_slow=90, atr_period=15, vol_ma_period=31, sl_atr_mult=2.6821, tp_atr_mult=6.8668

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/20260618_forge120_ema_supertrend]]
