---
coins:
- ETH
interest: Medium
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- aroon
- vortex
- ema_trend
- tight_atr
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #128 — Aroon Cross + Vortex Trend + EMA Trend Long + Tight ATR

## Concept
Aroon crossover (Aroon Up > Aroon Down + threshold) for trend inception detection, double-filtered by Vortex trend (VI+ > VI-) and long-term EMA trend. Tests the new Vortex Indicator as a filter in the forge pipeline.

## Entry Conditions
- Aroon cross: Aroon Up > Aroon Down + aroon_threshold

## Filter Conditions
- Vortex trend: VI+ > VI- (positive movement dominates)
- EMA trend long: close > long-period EMA macro filter

## Exit Conditions
- Tight ATR: SL = 0.97× ATR, TP = 5.68× ATR (R:R ≈ 5.86 — very asymmetric)

## Key Indicators
- Aroon Oscillator (new trend inception signal)
- Vortex Indicator VI+/VI- (new trend filter)
- Long EMA (macro trend)
- ATR exits

## Expected Edge
Triple confirmation (Aroon + Vortex + EMA) is very selective. The ultra-wide TP:SL ratio (5.86) means the strategy wins rarely but wins large — needs a sustained trend to pay off.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 3 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 128
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 0.78, ROI: 163%, MDD: 37%
- Params: aroon_period=12, aroon_threshold=67, vortex_period=19, ema_trend=214, atr_period=22, sl_atr_mult=0.966, tp_atr_mult=5.6814

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/20260618_forge120_ema_supertrend]]
