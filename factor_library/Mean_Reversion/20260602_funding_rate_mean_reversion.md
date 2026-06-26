---
coins: BTC, ETH, SOL
interest: High
name: Funding Rate Mean Reversion
source: Quantpedia and Crypto-specific quantitative research
status: IMPLEMENTED
tags:
- implemented
timeframes: 1h, 4h
type: mean-reversion
---
# Funding Rate Mean Reversion

## Concept
Mean reversion strategy that isolates a coin's performance and exploits over-extension using a combination of price Z-scores and taker_buy_base_vol (proxy for funding rate/sentiment extremes). Extremely high taker buy volume indicates overheated sentiment, often preceding a reversal, while extremely low indicates capitulation.

## Entry Conditions
- Long: Price Z-score < -2.0 AND taker_buy_base_vol extremely low (capitulation).
- Short: Price Z-score > +2.0 AND taker_buy_base_vol extremely high (overheated).

## Exit Conditions
- Take profit: When Z-score reverts to 0 (mean).
- Stop loss: Fixed percentage (e.g., 2-3%).

## Key Indicators
- Price Z-Score (Rolling 50-period SMA and standard deviation).
- Taker Buy Base Volume (Rolling Z-score or threshold).

## Expected Edge
Crypto markets are highly retail-driven and susceptible to rapid sentiment shifts. Extreme taker volume confirms the over-extension highlighted by the price Z-score, providing high-probability mean reversion setups.

## Data Requirements
- Columns needed: Close, Volume, taker_buy_base_vol
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Use rolling Z-scores to adapt to volatility regimes.
---
## Connections

**Category:** [[Mean_Reversion/_Index]]


**Related Factors:** [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Trend_Momentum/20260527_ema_ribbon_rsi_momentum]] · [[Mean_Reversion/20260527_aroon_rsi_mean_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]]
