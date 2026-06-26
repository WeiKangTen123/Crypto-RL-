---
coins: BTC, ETH, SOL
interest: High
name: fvg-mitigation-reversal
source: Web Research (Smart Money Concepts 2026)
status: REJECTED
tags:
- rejected
timeframes: 1h, 4h
type: short-term
---
# FVG Mitigation Reversal

## Rejection Notes (2026-05-27)
- **Result**: Sharpe Ratio -0.09 after optimization on BTC/4H (2023-2024).
- **Reason**: The strategy generates too many false signals in ranging markets and the simple mitigation logic (entering on any touch) leads to high drawdown. Even with gap size filtering (min_gap_pct up to 0.01), it failed to reach a positive Sharpe ratio.
- **Possible Improvements**: Add a higher-timeframe trend filter or a more sophisticated "first-touch" logic with order flow confirmation.

## Concept
Fair Value Gaps (FVG) occur when price moves so rapidly that it leaves an imbalance—a gap between the high of bar 1 and the low of bar 3 (for a bullish move). This strategy waits for price to return (mitigate) to this gap, treating it as a high-probability support/resistance zone.

## Entry Conditions
- **Bullish FVG (Imbalance)**:
    1. Identify gap: `Low[i] > High[i-2]` (for a bullish 3-bar sequence).
    2. Wait for price to pull back into this gap (between `High[i-2]` and `Low[i]`).
    3. Entry on bullish price action (e.g., bullish engulfing) inside the gap.
- **Bearish FVG (Imbalance)**:
    1. Identify gap: `High[i] < Low[i-2]` (for a bearish 3-bar sequence).
    2. Wait for price to pull back into this gap (between `Low[i-2]` and `High[i]`).
    3. Entry on bearish price action (e.g., bearish engulfing) inside the gap.

## Exit Conditions
- **Take Profit**: 2x the gap width or next structural level.
- **Stop Loss**: The "origin" candle of the FVG (High[i] for bullish, Low[i] for bearish).

## Key Indicators
- **FVG Detector**: Custom logic comparing `High[i-2]` and `Low[i]`.
- **Volume Filter**: Gap should be formed on high volume (momentum).

## Expected Edge
FVGs represent areas where the market was "unfairly" priced due to high momentum. Re-visiting these levels often finds "leftover" liquidity or institutional limit orders.

## Data Requirements
- Columns needed: Close, High, Low, Volume.
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- "Inversion FVG" (where a bullish gap becomes resistance) can also be a secondary signal.
- Gap size filter to avoid tiny, insignificant gaps.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/Order_Flow]]

**Related Factors:** [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260528_zero_lag_trend_speed_momentum]] · [[Trend_Momentum/20260527_triple_confirm_fvma_zerolag]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]]
