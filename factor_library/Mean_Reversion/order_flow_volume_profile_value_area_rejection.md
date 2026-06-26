## Strategy Name
Volume Profile Value Area (VA) Rejection & 80% Rule

## Category
Order Flow

## Core Hypothesis — WHY should this strategy have an edge?
Market participants tend to trade around "fair value"—the price range where 70% of the session's volume occurred. When price moves outside this Value Area (VA), it is in a state of imbalance. If price fails to sustain the breakout and re-enters the VA, it indicates that the move was an "uninformed" spike or a "stop run." The 80% Rule states that if price re-enters and holds within the previous VA for two 30m periods, there is a high probability of a full rotation to the opposite side of the VA, exploiting the "vacuum" of orders in the middle.

## Entry Signal — exact condition that triggers a buy
1. **The 80% Rule Setup:** Price opens below the previous day's Value Area Low (VAL).
2. **Re-entry:** Price closes back above VAL and sustains for two consecutive 30m candles.
3. **Trigger:** Buy on the close of the second 30m candle or on a 1h "retest" of the VAL.

## Exit Signal — exact condition that triggers a sell or position close
1. **Target 1:** Point of Control (POC)—the highest volume level.
2. **Target 2 (Final):** Value Area High (VAH)—the opposite side of the range.
3. **Stop Loss:** Below the recent swing low or back outside the VAL.

## Key Indicators / Data Required
- **Session Volume Profile**
- **Value Area High (VAH) / Value Area Low (VAL)**
- **Point of Control (POC)**
- **30m / 1h OHLCV**

## Timeframe Compatibility (scalp / swing / position)
- **30m / 1h:** Ideal for identifying intraday rotations.

## Theoretical Risk — what market conditions break this strategy?
Strongly trending markets ("Imbalance") where price breaks the VA and never returns. This strategy is purely for range-bound or mean-reverting environments.

## Source — URL or reference
- Developed by Dalton (Mind Over Markets) and refined for electronic trading.
- Popularized as the "80% Rule" in futures and crypto markets.

## Interest Rating — [High]
High — Volume Profile levels are among the most respected "invisible" support/resistance levels in crypto. A DRL agent can use these as dynamic inputs to understand whether price is "cheap" or "expensive" relative to recent history.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/Order_Flow]]
