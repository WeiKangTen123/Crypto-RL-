---
coins: BTC, ETH, BNB
interest: High
name: multi-tf-rsi-divergence
source: Pine Script v6 Community / RSI Divergence Detector
status: REJECTED
tags:
- rejected
timeframes: 15m, 1h, 4h
type: short-term
---
# Multi-TF RSI Divergence

## Rejection Notes
- Sharpe Ratio: -0.76
- Total Return: -7.41%
- Win Rate: 12.5% (1/8 trades)
- Observations: The strategy was highly selective but failed to capture profitable reversals. The 12.5% win rate suggests the divergence logic or the filters were either too restrictive or the momentum was too strong for simple reversals to work in the 2023 BTC market.

## Concept
Exploits bearish/bullish divergences between price and RSI across multiple timeframes simultaneously. A divergence on a higher timeframe (e.g., 4h) confirmed by a similar divergence on a lower timeframe (e.g., 1h) provides a high-probability reversal signal.

## Entry Conditions
- Long: Bullish RSI divergence on TF1 (e.g., 1h) AND Bullish RSI divergence on TF2 (e.g., 4h).
- Short: Bearish RSI divergence on TF1 AND Bearish RSI divergence on TF2.

## Exit Conditions
- Take profit: Fixed RR (2:1) or RSI overbought/oversold levels.
- Stop loss: Recent swing high/low.

## Key Indicators
- RSI (14)
- Divergence detection logic (lookback=50)

## Expected Edge
Divergences represent momentum exhaustion. Multi-timeframe confluence filters out "local" divergences that are often overrun by higher-timeframe trends.

## Data Requirements
- Columns needed: Close
- Minimum timeframe: 15m
- Minimum history: 1 year (multi-tf alignment)

## Implementation Notes
- Needs efficient logic to handle multiple timeframes without lookahead bias.
- Define "Divergence" strictly: Price makes a new high/low while RSI does not.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]]
