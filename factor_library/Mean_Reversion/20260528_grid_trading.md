---
coins: BTC
interest: High
name: grid-trading-btc
source: Web Search (Bravos Research)
status: COMPLETED
tags:
- built
- backtested
timeframes: 1h
type: short-term
---
# Grid Trading BTC

## Concept
Automated "buy low, sell high" within a defined price range to capture volatility during ranging markets.

## Entry Conditions
- Price is within the defined grid range [min_price, max_price].
- Each grid level acts as a buy/sell trigger.

## Exit Conditions
- Take profit: Grid boundary or total profit target.
- Stop loss: Below lower grid boundary.

## Key Indicators
- Grid level markers (defined by price bounds and number of grids).

## Expected Edge
Captures profit from sideways price action without needing a directional trend.

## Data Requirements
- Columns needed: Close
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Grid interval selection is critical.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]]
