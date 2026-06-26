# EMA Crossover Strategy

**Concept:** A trend-following strategy that generates buy and sell signals based on the crossover of two Exponential Moving Averages (EMAs).

**Source:** Inspired by common strategies found on TradingView.

**Logic:**
- **Buy Signal:** A short-term EMA (e.g., 5-period) crosses above a long-term EMA (e.g., 21-period).
- **Sell Signal:** The short-term EMA crosses below the long-term EMA.

**Potential Filters:**
- A third, even longer-term EMA (e.g., 55-period) to confirm the overall trend direction.
- Volume confirmation.

**Interest Score:** HIGH

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]]
