---
coins:
- ETH
interest: High
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- ema_cross
- williams_r
- tight_atr
- stable
- all_years_positive
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #127 — EMA Price Cross + WR Not Extreme + EMA Trend Short + Tight ATR ★ MOST STABLE

## Concept
Price crossing above a medium-period EMA for entry, filtered by Williams %R not-at-extreme (avoids buying overbought) and short-term EMA trend confirmation. Tight ATR exits (large TP:SL ratio) force only high-conviction trades to run.

## Entry Conditions
- EMA price cross: close crosses above ema_period EMA

## Filter Conditions
- WR not extreme: Williams %R between -90 and -10
- EMA trend short: close > ema_trend-period EMA

## Exit Conditions
- Tight ATR: SL = 2.30× ATR, TP = 6.54× ATR (R:R ≈ 2.84)

## Key Indicators
- Medium-period EMA (price cross trigger)
- Williams %R (not-extreme filter)
- Short EMA (trend filter)
- ATR (asymmetric exits)

## Expected Edge
Williams %R filter prevents buying into overbought conditions — the largest source of failed EMA cross entries. Asymmetric TP/SL (2.84 R:R) means fewer but larger wins.

## Performance (verified at 0.10 risk / 10x leverage)
- Sharpe: 1.24 | ROI: 283% | MDD: 26%
- ALL 5 years positive: 2022 +74%, 2023 +18%, 2024 +46%, 2025 +37%, 2026 (partial)
- Most consistent strategy across the full bear-to-bull cycle

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 4 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 127
- ETH/4h, risk 0.10, leverage 10x
- Params: ema_period=142, ema_trend=170, period=42, atr_period=16, sl_atr_mult=2.2999, tp_atr_mult=6.5362

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/20260618_forge125_fvg_taker_wr_atr]], [[Trend_Momentum/20260618_forge119_rsi_trend_stable]]
