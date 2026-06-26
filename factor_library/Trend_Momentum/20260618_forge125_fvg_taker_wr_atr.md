---
coins:
- ETH
interest: High
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- fvg
- fair_value_gap
- taker_confirm
- williams_r
- atr
- elite
- implemented
timeframes:
- 4h
type: order-flow
---
# FORGE #125 — FVG + Taker Confirm + Williams %R Filter + ATR Hold ★ BEST

## Concept
Fair Value Gap (institutional imbalance signal) entry filtered by taker buy confirmation (smart money flow) and Williams %R not-at-extreme filter (avoids overbought entries). Exits via ATR TP/SL with max hold bar cap.

## Entry Conditions
- FVG signal: bullish fair value gap detected (gap between two candles indicating institutional buying)

## Filter Conditions
- Taker confirm: taker buy ratio above threshold (smart money flow confirmation)
- WR not extreme: Williams %R between -90 and -10 (not overbought/oversold)

## Exit Conditions
- ATR TP/SL Hold: TP at tp_atr_mult=4.60× ATR, SL at sl_atr_mult=1.97× ATR, max hold=140 bars

## Key Indicators
- Fair Value Gap (structure imbalance)
- Taker buy intensity
- Williams %R (-100 to 0 oscillator)
- ATR exits

## Expected Edge
FVG entries target institutional order blocks — price often returns to fill gaps with strong momentum. Dual confirmation (taker flow + WR) eliminates retail noise. ATR exits capture the trend leg without overstaying.

## Performance (verified at 0.10 risk / 10x leverage)
- Sharpe: 1.46 | ROI: 854% | MDD: 40% | Monthly: ~5%
- 2022: +67%, 2023: -10%, 2024: +141%, 2025: +101%, 2026: +31%

## Data Requirements
- Columns needed: Close, High, Low, taker_buy_volume, volume
- Minimum timeframe: 4h
- Minimum history: 4 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 125 — BEST overall strategy
- ETH/4h, risk 0.10, leverage 10x
- Params: atr_period=24, intensity_period=13, period=43, tp_atr_mult=4.6029, sl_atr_mult=1.9697, max_hold_bars=140

---
## Connections

**Category:** [[Trend_Momentum/_Index]]


**Related Factors:** [[Trend_Momentum/20260618_forge117_zlema_taker_maxhold]], [[Trend_Momentum/20260618_forge127_ema_wr_short_tight]]
