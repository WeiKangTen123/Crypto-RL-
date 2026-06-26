---
coins: BTC, ETH, SOL
interest: High
name: aroon-rsi-mean-reversion
source: Custom / TradingView
status: REJECTED
tags:
- rejected
timeframes: 1h, 4h
type: short-term
---
# Aroon RSI Mean Reversion

## Concept
This strategy identifies extreme overextended conditions using the Aroon Oscillator and RSI. When both indicators signal an exhaustive state (Aroon at extremes and RSI overbought/oversold), it bets on a reversion to the mean. It is particularly effective in ranging or choppy markets where price tends to bounce between levels.

## Entry Conditions
- **Long**: 
    - Aroon Down > 70 (Strong downward trend exhaustion)
    - RSI < 30 (Oversold)
    - Price closes above the 10-period EMA (Confirmation of pivot)
- **Short**:
    - Aroon Up > 70 (Strong upward trend exhaustion)
    - RSI > 70 (Overbought)
    - Price closes below the 10-period EMA (Confirmation of pivot)

## Exit Conditions
- **Take Profit**: 2.5 * ATR (Average True Range) or when RSI crosses the midpoint (50).
- **Stop Loss**: 1.5 * ATR or below the recent swing low/high.

## Key Indicators
- Aroon (14)
- RSI (14)
- EMA (10)
- ATR (14)

## Expected Edge
Crypto markets often exhibit high volatility spikes followed by quick reversions. By combining a trend-strength indicator (Aroon) with a momentum oscillator (RSI), we filter for high-probability exhaustion points rather than just simple oscillator levels.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume.
- Minimum timeframe: 1h
- Minimum history: 1 year

## Implementation Notes
- Use `ta.AROON` and `ta.RSI` from TA-Lib or similar.
- Consider adding a volatility filter (e.g., ADX < 25) to ensure we are in a ranging regime.

## Rejection Notes
- **Performance**: Sharpe -1.91 on BTC 4H (2023).
- **Drawdown**: 44.5% Max Drawdown.
- **Status**: REJECTED on 2026-05-27.

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]] · [[Mean_Reversion/20260526_rsi_divergence_reversal]] · [[Mean_Reversion/20260526_rsi_divergence_mean_reversion]] · [[Mean_Reversion/20260526_keltner_rsi_reversion]]
