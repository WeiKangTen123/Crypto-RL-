---
coins: BTC, ETH, SOL
interest: High
name: order-block-smc-reversal
source: TradingView (LuxAlgo SMC)
status: IMPLEMENTED
tags:
- research
- implemented
timeframes: 1h, 4h
type: short-term
---
# Order Block (SMC) Reversal Strategy

## Concept
Identifies "Order Blocks" (last down candle before a strong up move, or last up candle before a strong down move) as institutional liquidity zones. Trades reversals when price returns to these zones (mitigation).

## Math/Logic
1. **Strong Move Detection**: An impulse move where absolute return over 3 bars > 2.0 * ATR(14).
2. **Order Block (OB) Identification**:
   - Bullish OB: The last Bearish candle before a Bullish Strong Move. OB Zone = [High, Low] of that candle.
   - Bearish OB: The last Bullish candle before a Bearish Strong Move. OB Zone = [High, Low] of that candle.
3. **Mitigation Check**:
   - A Bullish OB is 'Mitigated' when price falls back and touches the OB zone (specifically the High of the OB candle).
   - Signal: 1 (Long) on the first touch of an unmitigated Bullish OB.
   - Signal: -1 (Short) on the first touch of an unmitigated Bearish OB.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Trend_Momentum/20260527_Adaptive_FreqAI_Momentum]] · [[Mean_Reversion/20260526_liquidity_sweep_reversal]]
