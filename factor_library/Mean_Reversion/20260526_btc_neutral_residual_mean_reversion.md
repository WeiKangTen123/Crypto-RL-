---
coins: ETH, BNB, SOL, XRP
interest: High
name: btc-neutral-residual-mean-reversion
source: X.com / Quant Blogs
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: short-term
---
# BTC-Neutral Residual Mean Reversion

## Concept
Uses rolling regression to calculate "residual returns" for altcoins (ETH, SOL, etc.) net of Bitcoin's influence. It bets on idiosyncratic coin movements reverting to their specific mean, independent of the broader market trend.

## Entry Conditions
- Calculate Beta of Altcoin vs BTC (rolling 30-day).
- Calculate Residual = Return_Alt - Beta * Return_BTC.
- Buy if Z-score of Residual < -2.
- Sell if Z-score of Residual > +2.

## Exit Conditions
- Take profit: Residual Z-score returns to 0.
- Stop loss: Residual Z-score hits +/- 4.

## Key Indicators
- Beta (Alt vs BTC)
- Residual Return
- Z-score of Residual

## Expected Edge
Removes "beta" (market) risk and focuses on specific coin anomalies that are more likely to mean-revert.

## Data Requirements
- Columns needed: Close (Alt and BTC)
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- Requires concurrent loading of BTC data for every Altcoin being tested.
- Residual calculation must be rolling to adapt to changing market correlations.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Related Factors:** [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Volatility_Breakout/bb_squeeze_breakout]] · [[Trend_Momentum/mtf_macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj_adx_atr]] · [[Trend_Momentum/macd_kdj]] · [[Trend_Momentum/20260527_taker_buy_intensity_momentum]]
