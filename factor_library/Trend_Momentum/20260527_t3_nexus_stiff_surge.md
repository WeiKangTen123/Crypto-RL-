---
coins: BTC, ETH, SOL
interest: High
name: t3-nexus-stiff-surge
source: YouTube (Davidd Tech) / TradingView
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: trend-following
---
# T3 Nexus + Stiff Surge

## Concept
This strategy combines the T3 Moving Average (Nexus) for smooth trend identification with the Waddah Attar Explosion (WAE) and a "Stiff" filter to capture high-momentum breakouts while avoiding choppy price action.

## Entry Conditions
- **Long**:
    - Price is above T3 Moving Average (Length: 25).
    - Waddah Attar Explosion (WAE) bar is green and above the dead zone line.
    - Stiff filter (based on momentum slope) is positive.
- **Short**:
    - Price is below T3 Moving Average (Length: 25).
    - Waddah Attar Explosion (WAE) bar is red and above the dead zone line.
    - Stiff filter is negative.

## Exit Conditions
- **Take Profit**: 2:1 Risk/Reward ratio or when T3 color changes.
- **Stop Loss**: Recent swing high/low or 1.5 * ATR.

## Key Indicators
- **T3 Moving Average**: Length 25, Volume Factor 0.7.
- **Waddah Attar Explosion**: Standard settings (Sensitive: 150, DeadZone: 20).
- **Stiff Filter**: Custom momentum-based smoothing.

## Expected Edge
T3 provides superior smoothing compared to EMA, reducing false signals in ranging markets. WAE confirms volume-backed moves, ensuring we only enter when there is sufficient market "explosion".

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume.
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- T3 calculation requires specific smoothing logic (Tillson's T3).
- WAE needs careful deadzone calibration for different coins.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260528_zero_lag_trend_speed_momentum]] · [[Trend_Momentum/20260527_triple_confirm_fvma_zerolag]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]]
