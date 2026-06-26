---
coins: BTC, ETH, SOL
interest: High
name: z-score-stat-arb
source: Research (Statistical Arbitrage)
status: IMPLEMENTED
tags:
- queued
- implemented
timeframes: 1h, 4h
type: short-term
---
# Z-Score Statistical Arbitrage

## Concept
Uses the Z-Score to measure how many standard deviations the current price is away from its 20-period moving average. It bets on the price returning to the mean (Z-Score = 0) when it reaches extreme levels (±3.0).

## Entry Conditions
- Buy: Z-Score < -3.0 and price shows a reversal candle (e.g., hammer or bullish engulfing).
- Sell: Z-Score > +3.0 and price shows a reversal candle.

## Exit Conditions
- Take profit: Z-Score crosses 0.
- Stop loss: Z-Score reaches ±4.0 or fixed % based on ATR.

## Key Indicators
- Z-Score (20-period)
- ATR (14-period) for stop loss

## Expected Edge
Crypto prices often overextend during liquidations or FOMO. Statistical extremes are likely to mean-revert as liquidity stabilizes.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Need to calculate rolling mean and rolling std dev for Z-Score.
- Reversal candle detection adds a layer of confirmation to avoid "catching a falling knife".

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]]

**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]] · [[Mean_Reversion/20260526_liquidity_sweep_reversal]]
