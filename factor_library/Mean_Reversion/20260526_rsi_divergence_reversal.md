---
coins: BTC, ETH, SOL, BNB
interest: High
name: rsi-divergence-momentum-reversal
source: Web Search (2026 Reversal Strategies)
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: short-term
---
# RSI Divergence Momentum Reversal

## Concept
Exploits momentum exhaustion by identifying divergences between price action and the Relative Strength Index (RSI). A bullish divergence (Lower Low in price, Higher Low in RSI) signals a potential bottom.

## Entry Conditions
- Bullish Divergence: Price makes a lower low while RSI (14) makes a higher low (both RSI lows should be < 30).
- Confirming Candle: A bullish engulfing or hammer candle on the 1h/4h timeframe.
- Taker Buy Intensity > 0.5 (optional filter).

## Exit Conditions
- Take profit: RSI reaches 70 or price hits a recent swing high.
- Stop loss: Just below the recent price lower low.

## Key Indicators
- RSI (14).
- Taker Buy/Sell Volume (for intensity filter).

## Expected Edge
Divergences are high-probability setups in crypto, especially on higher timeframes like 4h, where they signal major regime shifts.

## Data Requirements
- Columns needed: Close, taker_buy_base_vol, Volume.
- Minimum timeframe: 1h.

## Implementation Notes
- Detecting divergences programmatically requires identifying local peaks/troughs in both price and RSI.
- Use a lookback window of 20-50 bars for divergence detection.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]]
