---
coins: BTC, ETH, SOL
interest: High
name: dynamic-swing-anchored-vwap
source: TradingView / 2026 Trend Analysis
status: QUEUED
tags:
- queued
timeframes: 1h
type: short-term
---
# Dynamic Swing Anchored VWAP

## Concept
Anchored VWAP (AVWAP) is a powerful tool for identifying institutional value areas. This strategy dynamically "anchors" the VWAP to the most recent significant swing high or swing low and uses price interactions with the AVWAP as entry/exit signals.

## Entry Conditions
- Long: Price breaks above AVWAP anchored at the recent swing low.
- Short: Price breaks below AVWAP anchored at the recent swing high.
- Confirmation: Volume expansion at the breakout point.

## Exit Conditions
- Take profit: Fixed 3:1 RR or break back below/above AVWAP.
- Stop loss: Below/above the anchor candle or ATR-based (2.0 * ATR).

## Key Indicators
- Anchored VWAP
- Swing High/Low Detection (Lookback: 20-50 bars)
- ATR (14)

## Expected Edge
Institutional orders often cluster around price levels where a trend started (swing high/low). AVWAP represents the average price since that pivot, acting as a dynamic support/resistance that reflects market participation.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Requires a robust swing detection algorithm.
- "Anchoring" needs to reset whenever a new significant swing is formed.
\n## Rejection Notes\nOptimization across 81 combinations yielded a maximum Sharpe Ratio of 0.54 with only 9.7% return. The edge is too weak to survive WFO. Discarded.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]]
