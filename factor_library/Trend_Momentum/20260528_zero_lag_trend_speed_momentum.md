---
coins: BTC, ETH, SOL
interest: High
name: 20260528_zero_lag_trend_speed_momentum
source: GitHub (HKUDS/Vibe-Trading) / TradingView (Trend Speed Analyzer)
status: REJECTED
tags:
- rejected
timeframes: 1h, 4h
type: short-term
---
# Zero-Lag Trend Speed Momentum

## Rejection Notes
- Sharpe Ratio: -4.31
- Total Return: -93.80%
- Win Rate: 28.04%
- Observations: The strategy suffered from extreme over-trading (699 trades in 1 year) and was heavily penalized by fees. The dynamic exit logic likely triggered too frequently, cutting winners too early or entering during chop. Momentum Z-Score threshold might be too low, or the combination of acceleration and Z-Score is not selective enough in 1H crypto markets.

## Concept
This strategy combines high-velocity technical momentum with a zero-lag filter to capture parabolic moves early and exit before the trend exhausts. It leverages the "Trend Speed" concept which measures the velocity (Slope 1) and acceleration (Slope 2) of price action.

## Entry Conditions
- Price must be above the Zero-Lag EMA (ZLEMA).
- Trend Speed (Slope 1) must be positive and increasing (Acceleration > 0).
- Momentum (Z-Score of price change) must cross above 1.5.

## Exit Conditions
- Take profit: 3 * ATR or when Trend Speed starts to decelerate (Slope 2 < 0) while Slope 1 is still positive.
- Stop loss: 1.5 * ATR below entry price.

## Key Indicators
- ZLEMA (Length: 20)
- Trend Speed (Velocity: Slope of 5-period EMA; Acceleration: Slope of Velocity)
- ATR (Length: 14) for dynamic SL/TP

## Expected Edge
Crypto markets often exhibit high momentum and parabolic phases. Traditional moving averages lag significantly, missing the meat of the move or exiting too late. Zero-lag filters and velocity-based trend detection allow for faster reaction times during "parabolic" regimes common in 2026.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Use a 100-period lookback for Z-Score normalization of momentum.
- Slope should be calculated as the difference between current and previous value, optionally smoothed.
- Consider adding a "Vibe" filter later if sentiment data is available.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_triple_confirm_fvma_zerolag]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]]
