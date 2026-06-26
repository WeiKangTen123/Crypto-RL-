---
coins: BTC, ETH, SOL
interest: High
name: Dump Reversal Peak Trail (DRPT)
source: GitHub (GeekTrade/TradingView-Strategies)
status: REJECTED
tags:
- rejected
timeframes: 5m, 15m
type: short-term
---
# Dump Reversal Peak Trail (DRPT)

## Concept
Identifies extreme downward price anomalies (dips) that break N-period lows with high volume (dump). Instead of blind entry, it waits for a confirmed reversal (e.g., green candle close or specific RSI recovery) to avoid "falling knives."

## Entry Conditions
- Price breaks the 24-hour low.
- Volume is at least 2x the average volume of the last 20 periods.
- Reversal Signal: A green candle closes after the dump, or RSI(14) crosses back above 30.

## Exit Conditions
- Take profit: Peak-retrace trailing stop of 2%.
- Stop loss: 1.5% below the entry low.

## Key Indicators
- Donchian Channels (24h period) for low identification.
- Volume MA (20 period).
- RSI (14).

## Expected Edge
Exploits mean-reversion following panic selling or liquidation cascades in highly liquid crypto assets.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume.
- Minimum timeframe: 5m.
- Minimum history: 1 year.

## Implementation Notes
- Needs careful handling of trailing stops to capture fast rebounds.
- SOL/USDT is a primary target due to its high volatility and frequent mean-reversion after spikes/dips.

## Rejection Notes (2026-05-26)
- **Quick Backtest (SOL/5M)**: Sharpe -1.50, Return -100%. 1113 trades.
- **Optimization Sweep**: Tested lookbacks (288, 576), multipliers (3, 5, 8), and trailing stops. Best Sharpe found was -0.75.
- **Reason**: High trade frequency and low win rate (16-36%) led to massive drawdowns and fee erosion. The "reversal" signal (green close/RSI cross) is too late or too frequent, resulting in many false entries during extended downtrends (catching the knife).

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Mean_Reversion/20260527_aroon_rsi_mean_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]]
