---
coins: BTC, ETH, SOL
interest: High
name: golden-zone-fib-bos
source: Web Research (2026 trend)
status: COMPLETED
tags:
- built
- backtested
- REJECTED
timeframes: 1h, 4h
type: short-term
---
# Golden Zone Fibonacci BOS

## Concept
The strategy exploits institutional retracements following a Break of Structure (BOS). It identifies a structural shift (higher high or lower low), then waits for a retracement into the "Golden Zone" (0.618 Fibonacci level) before entering in the direction of the new trend.

## Entry Conditions
- **Long**: 
    1. Break of Structure (BOS): Price closes above the previous swing high.
    2. Retracement: Price touches the 0.618 Fibonacci retracement level of the swing leg (from swing low to new high).
    3. Bullish Confirmation: A bullish engulfing or pin bar at the 0.618 level (optional, can use RSI oversold).
- **Short**:
    1. Break of Structure (BOS): Price closes below the previous swing low.
    2. Retracement: Price touches the 0.618 Fibonacci retracement level of the swing leg (from swing high to new low).
    3. Bearish Confirmation: A bearish engulfing or pin bar at the 0.618 level.

## Exit Conditions
- Take profit: 1.618 Fibonacci extension of the swing leg.
- Stop loss: Below the 0.786 Fibonacci level (protects against deeper retracements).

## Key Indicators
- Fractal Highs/Lows (to identify swing points)
- Fibonacci Retracement (0.618, 0.786)
- Fibonacci Extension (1.618)
- ATR (for dynamic SL padding)

## Expected Edge
Capitalizes on "Order Block" mitigation and liquidity sweeps. Institutions often fill their remaining orders at the 0.618 level after causing a BOS.

## Data Requirements
- Columns needed: Open, High, Low, Close
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Requires a robust swing point identification algorithm (e.g., Donchian Channels or Pivot Points).
- Must handle overlapping swing legs.
\n## Rejection Notes\nFailed quick backtest. Sharpe Ratio: -0.95, Win Rate: 18.37%, Profit Factor: 0.92.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]] · [[Mean_Reversion/20260526_liquidity_sweep_reversal]]
