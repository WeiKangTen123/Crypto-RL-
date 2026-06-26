## Strategy Name
Intraday Session Opening Range Breakout (ORB)

## Category
Volatility

## Core Hypothesis — WHY should this strategy have an edge?
While Bitcoin trades 24/7, institutional liquidity and volatility are concentrated during the opening hours of major traditional stock exchanges (London at 3:00 AM EST and New York at 9:30 AM EST). The price action during the first 30-60 minutes of these sessions often sets the "tone" or the directional bias for the rest of the day. A breakout from this initial range indicates that one side (buyers or sellers) has won the initial auction and is aggressively pushing price into a new trend.

## Entry Signal — exact condition that triggers a buy
1. **The Range:** Mark the High and Low of the first 30 minutes of the London Session (03:00–03:30 EST) or NY Session (09:30–10:00 EST).
2. **The Breakout:** Wait for a 30m or 1h candle to close clearly above the session high (for longs) or below the session low (for shorts).
3. **Volume Confirmation:** The breakout candle must have volume higher than the 10-period volume SMA.

## Exit Signal — exact condition that triggers a sell or position close
1. **Profit Target:** Previous day's high/low or a 2.0 extension of the session range.
2. **Stop Loss:** Back inside the 30m opening range (specifically below the 50% "midpoint" of the range).
3. **Time Exit:** Close at the end of the session (e.g., 4:00 PM EST for NY trades).

## Key Indicators / Data Required
- **Session High / Low (First 30m)**
- **Volume SMA**
- **30m / 1h OHLCV**

## Timeframe Compatibility (scalp / swing / position)
- **30m / 1h:** Ideal for capturing the daily expansion move.

## Theoretical Risk — what market conditions break this strategy?
"Mid-Session Reversals" where a strong breakout occurs but then is completely faded as liquidity dries up. This often happens on low-impact news days.

## Source — URL or reference
- Classic trading concept by Toby Crabel (Opening Range Breakout).
- Adapted for crypto markets with session-specific timing (Kill Zones).

## Interest Rating — [Medium-High]
High — Session timing is one of the most underrated features in DRL crypto bots. By teaching the agent to "watch the clock," it can learn to avoid low-volatility chop and only enter when institutional momentum is highest.

---
## Connections

**Category:** [[Volatility_Breakout/_Index]]

**Indicators:** [[_Concepts/SMA]]
