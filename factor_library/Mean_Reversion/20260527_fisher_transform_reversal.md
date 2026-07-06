---
coins: BTC, ETH, SOL, BNB, XRP
interest: High
name: fisher-transform-reversal
source: Ehlers (2002) / TradingView
status: COMPLETED
tags:
- built
- backtested
- finetuned
- BAD
timeframes: 5m, 15m, 1h
type: short-term
---
# Fisher Transform Reversal

## Concept
The Fisher Transform, developed by John Ehlers, transforms prices into a Gaussian normal distribution. This makes extreme price movements much more visible and creates sharp, clear turning points. This strategy looks for "spikes" in the Fisher Transform and its signal line to identify early reversal opportunities.

## Entry Conditions
- **Long**: 
    - Fisher Transform value < -1.5 (Oversold spike)
    - Fisher Transform crosses above its Signal Line (EMA of Fisher)
- **Short**:
    - Fisher Transform value > 1.5 (Overbought spike)
    - Fisher Transform crosses below its Signal Line (EMA of Fisher)

## Exit Conditions
- **Take Profit**: Fixed ROI 2-3% or Fisher crossing back through 0.
- **Stop Loss**: Fixed 1-1.5% or ATR-based.

## Key Indicators
- Fisher Transform (9 or 10 period)
- Signal Line (EMA of Fisher, 9 period)

## Expected Edge
The Fisher Transform is known for its low lag and ability to identify turning points earlier than standard oscillators like RSI or Stochastic. In the fast-moving crypto market, this "lead time" can be the difference between a winning scalp and a late entry.

## Data Requirements
- Columns needed: High, Low, Close.
- Minimum timeframe: 5m (Scalping) or 1h (Swing).
- Minimum history: 6 months.

## Implementation Notes
- The Fisher Transform formula involves `0.33 * 2 * ((Value - Min) / (Max - Min) - 0.5) + 0.67 * LastValue`.
- It is sensitive to outliers, so look-back period (e.g., 10) is critical.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]] · [[Trend_Momentum/20260527_nowo_ichimoku_mtf]]
