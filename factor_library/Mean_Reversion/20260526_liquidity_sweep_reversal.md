---
coins: BTC, ETH, SOL
interest: High
name: liquidity-sweep-reversal
source: Web Research (Institutional Liquidity Patterns 2026)
status: COMPLETED
tags:
- built
- backtested
timeframes: 1h, 4h
type: short-term
---
# Liquidity Sweep & Reversal

## Concept
This strategy identifies "liquidity sweeps" where price briefly breaks a key structural level (swing high/low) to trigger stop-losses, followed by a rapid reversal. We use Cumulative Volume Delta (CVD) to confirm exhaustion—if price sweeps lower but CVD selling pressure is diminishing, it indicates institutional absorption.

## Entry Conditions
- **Bullish Sweep**:
    1. Price breaks below the recent Swing Low (e.g., 20-period low).
    2. Price closes back above that Swing Low within 1-3 bars.
    3. (Optional) CVD shows lower selling volume on the sweep compared to the previous move.
- **Bearish Sweep**:
    1. Price breaks above the recent Swing High (e.g., 20-period high).
    2. Price closes back below that Swing High within 1-3 bars.
    3. (Optional) CVD shows lower buying volume on the sweep compared to the previous move.

## Exit Conditions
- **Take Profit**: Next major Swing High/Low or fixed 3:1 Reward-to-Risk ratio.
- **Stop Loss**: Just below/above the candle that performed the sweep.

## Key Indicators
- **Swing High/Low**: 20-period Donchian Channel or custom pivot points.
- **CVD (Cumulative Volume Delta)**: Derived from `taker_buy_base_vol` vs total volume.
  `delta = 2 * taker_buy_base_vol - volume`
  `cvd = delta.cumsum()`

## Expected Edge
Capitalizes on "stop-hunting" behavior by institutions. By waiting for the "re-entry" into the previous range, we avoid being caught in the initial breakout trap.

## Data Requirements
- Columns needed: Close, High, Low, Volume, taker_buy_base_vol.
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Sensitivity of "Swing Low/High" is critical.
- CVD confirmation helps filter out genuine breakouts.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/Order_Flow]]

**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]]
