## Strategy Name
MACD Zero-Cross

## Category
Trend Following

## Core Hypothesis — WHY should this strategy have an edge?
The MACD Zero-Cross signals that the short-term Exponential Moving Average (12) has crossed the long-term EMA (26). This represents a shift in the mathematical "equilibrium" of the price, suggesting that a new momentum-driven trend is establishing itself.

## Entry Signal — exact condition that triggers a buy
1. **Zero-Line Cross:** The MACD Line (12, 26) crosses from below 0.00 to above 0.00.
2. **Macro Filter:** (Optional) BTC price must be above the 200-day Simple Moving Average (SMA) to confirm macro bullishness.

## Exit Signal — exact condition that triggers a sell or position close
1. **Standard Exit:** MACD Line crosses back below the Zero Line.
2. **Aggressive Exit:** MACD Line crosses below the Signal Line (9-period EMA of MACD) to lock in gains before the trend fully reverses.

## Key Indicators / Data Required
- OHLCV Data
- MACD Indicator (Settings: 12, 26, 9)
- 200-day SMA (for trend filtering)

## Timeframe Compatibility (scalp / swing / position)
- **Swing:** 4H and 1D charts (Most reliable).
- **Not recommended for scalping** due to significant indicator lag.

## Theoretical Risk — what market conditions break this strategy?
- **Lag:** Because it relies on two EMAs, the signal often occurs after a significant portion of the move has already happened.
- **Sideways Whipsaw:** In ranging markets, the EMAs converge and cross frequently, creating "noise" signals that result in drawdown.

## Source — URL or reference
https://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:moving_average_convergence_divergence_macd

## Interest Rating — [Medium] with one-line reason
Medium - Useful as a macro-regime indicator for a DRL model, but potentially too lagging for a primary entry trigger in high-speed BTC markets.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]] · [[_Concepts/MACD]] · [[_Concepts/SMA]]
