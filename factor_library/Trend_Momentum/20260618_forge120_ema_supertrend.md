---
coins:
- ETH
interest: High
name: FORGE
source: AlphaForgeV2 RandomSearch
status: IMPLEMENTED
tags:
- forge
- ema_cross
- supertrend
- trailing_stop
- implemented
timeframes:
- 4h
type: trend-momentum
---
# FORGE #120 — EMA Cross + Supertrend Trail

## Concept
Classic EMA crossover entry signal combined with Supertrend trailing stop for dynamic exit management. The supertrend adapts the stop-loss to current volatility, allowing profitable trends to run while cutting losses in reversals.

## Entry Conditions
- Fast EMA crosses above slow EMA

## Filter Conditions
- None (clean signal)

## Exit Conditions
- Supertrend trail: exit when price crosses below the supertrend line (ATR-based dynamic stop)

## Key Indicators
- EMA crossover (entry)
- Supertrend (ATR-based trailing stop)

## Expected Edge
Supertrend trails reduce MDD versus fixed stop losses — the stop tightens after strong moves but widens when volatility increases, balancing profit protection with trend continuation.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 3 years

## Implementation Notes
- Registered as ForgeStrategy in settings.py ID 120
- ETH/4h, risk 0.10, leverage 10x
- Sharpe: 1.49 (highest in V2 batch at conservative risk)

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/EMA]]

**Related Factors:** [[Trend_Momentum/20260526_supertrend_atr_momentum]]
