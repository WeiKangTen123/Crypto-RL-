---
coins: BTC, ETH, SOL
interest: High
name: Dump Reversal
source: GitHub (GeekTrade/Dump-Reversal-Peak-Trail)
status: REJECTED
tags:
- rejected
timeframes: 15m, 1h
type: short-term
---
# Dump Reversal

## Concept
... (existing content) ...

## Rejection Notes
- Backtest (2023-01-01 to 2024-01-01) on BTC 15m showed a Sharpe Ratio of -0.46.
- Total trades: 106, Win Rate: 34.91%.
- Strategy failed to capture recoveries effectively with the default parameters, resulting in a -10.41% return.
- High frequency of signals in volatile conditions led to multiple stop-outs.
Exploits extreme capitulation events (flash crashes) by identifying "dump anomalies" and entering on the first sign of recovery.

## Entry Conditions
- Price breaks below a multi-day low (e.g., 5-day low).
- Volume is significantly higher than average (e.g., 2x average).
- Wait for a "confirmed green close" (Close > Open) on the chosen timeframe.

## Exit Conditions
- Take profit: Peak-retrace trailing exit (e.g., exit if price drops 2% from its post-entry peak).
- Stop loss: Fixed percentage below entry or lowest low of the dump.

## Key Indicators
- Multi-day Low (Price channel)
- Volume (SMA 20)
- Peak-Retrace Trailing Stop logic

## Expected Edge
Captures the "v-shape recovery" common in crypto after liquidation cascades.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume
- Minimum timeframe: 15m
- Minimum history: 1 year

## Implementation Notes
- Needs high-resolution data (15m) to catch the recovery early.
- Trailing stop must be dynamic to lock in gains during volatile rebounds.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]


**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]] · [[Mean_Reversion/20260526_liquidity_sweep_reversal]]
