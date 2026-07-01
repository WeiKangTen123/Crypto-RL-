---
coins: BTC, ETH
interest: High
name: trend-intensity-index-tii
source: M.H. Pee / TradingPedia
status: IN_PROGRESS
tags:
- built
- backtested
timeframes: 4h, 1d
type: short-term | long-term
---
# Trend Intensity Index (TII)

## Concept
The TII measures the strength of a trend by calculating the percentage of positive deviations from a long-term SMA. It is a robust momentum indicator that filters out market noise.

## Entry Conditions
- **Long (Trend Following)**:
    1. TII (60, 30) crosses above 80.
    2. Optional: Price above 200 SMA.

- **Short (Trend Following)**:
    1. TII (60, 30) crosses below 20.
    2. Optional: Price below 200 SMA.

## Exit Conditions
- Take profit: TII crosses back through 50 or fixed RR.
- Stop loss: 2x ATR or TII reversing direction.

## Key Indicators
- TII (Major: 60, Minor: 30)
- 200 SMA

## Expected Edge
TII captures the "intensity" of a move by looking at the distribution of closes relative to a mean. Values above 80 indicate that the majority of recent price action is consistently above the mean, signifying a powerful trend.

## Data Requirements
- Columns needed: Close.
- Minimum timeframe: 4h
- Minimum history: 2 years (for 60-period SMA on 4h).

## Rejection Notes
- **WFO Failure**: Failed 3/4 windows in Walk-Forward Validation.
- **Overfitting**: High Sharpe in 2023 (3.0+) but negative Sharpe in 2024, 2025, and 2026.
- **Regime Sensitivity**: Strongly biased towards the 2023 recovery regime.
- **Status**: REJECTED on 2026-05-27.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260528_zero_lag_trend_speed_momentum]] · [[Trend_Momentum/20260527_triple_confirm_fvma_zerolag]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]]
