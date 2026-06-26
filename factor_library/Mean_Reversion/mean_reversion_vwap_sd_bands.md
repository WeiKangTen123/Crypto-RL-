## Strategy Name
VWAP Mean Reversion & Trend Continuation (The "Anchor" Strategy)

## Category
Mean Reversion (VWAP reversion, intraday volume analysis)

## Core Hypothesis — WHY should this strategy have an edge?
Volume-Weighted Average Price (VWAP) is the "true North" for intraday traders. It represents the average price paid throughout the session, adjusted for volume. Professional desks and institutional algos often use VWAP as their execution benchmark. When price moves significantly away from VWAP without an impulsive "breakout" volume, it is considered overextended and likely to return to "fair value." Conversely, if price tests VWAP and holds it with high volume, it signals a strong trend continuation. This strategy targets the high-probability "snap-back" moves when price is 2-3 standard deviations away from the VWAP.

## Entry Signal — exact condition that triggers a buy
**Long Entry (Mean Reversion):**
1. **Timeframe:** 15-minute OHLCV (referencing `/dataset/BTC/15m`).
2. **Indicator:** VWAP with 1st, 2nd, and 3rd Standard Deviation Bands.
3. **Condition:** Price touches or breaks below the **3rd Lower Standard Deviation Band**.
4. **Confirmation:** RSI (14) must be below 30 (oversold) and showing a bullish divergence on the 5-minute timeframe.
5. **Trigger:** Enter when a 15m candle closes back **inside** the 2nd Standard Deviation Band.

**Short Entry (Mean Reversion):**
1. **Condition:** Price touches or breaks above the **3rd Upper Standard Deviation Band**.
2. **Confirmation:** RSI (14) must be above 70 (overbought).
3. **Trigger:** Enter when a 15m candle closes back **inside** the 2nd Standard Deviation Band.

## Exit Signal — exact condition that triggers a sell or position close
1. **Target 1:** The VWAP line (Mean).
2. **Target 2:** The opposite 1st Standard Deviation Band.
3. **Stop Loss:** Placed strictly outside the 3rd SD Band (0.5% buffer).
4. **Time Exit:** End of the trading session (close all positions before the daily reset).

## Key Indicators / Data Required
- **Price Data:** 15m OHLCV.
- **VWAP:** Resetting daily.
- **Standard Deviation Bands:** Calculated based on intraday volatility.
- **RSI:** Period 14.

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** Intraday (Scalp/Active trading).
- **Frequency:** High (Signals occur daily).

## Theoretical Risk — what market conditions break this strategy?
1. **Parabolic Trends:** During a "God Candle" or a massive liquidation event, price can stay pinned to the 3rd SD band for hours, blowing through stop-losses.
2. **Low Volume "Drift":** If price drifts away on low volume, the "snap-back" may never happen, leading to time-decay losses.
3. **News Events:** Unexpected macro news (Fed, SEC) invalidates intraday technical levels.

## Source — URL or reference
Standard institutional intraday trading protocol; adapted for BTC's 24/7 market where VWAP is typically reset at 00:00 UTC.

## Interest Rating — [High] with one-line reason
High - This is the most "active" trading strategy possible with OHLCV data, making it a perfect training ground for a DRL agent to learn intraday volatility.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]] · [[_Concepts/VWAP]]
