---
coins: ETH
interest: High
name: eth-layered-reversion
source: Internal — contrarian scalper concept
status: IMPLEMENTED
tags:
- implemented
timeframes: 1h
type: short-term
---
# ETH Layered Mean Reversion Strategy

## Concept
Contrarian scalper for ETH. Enters when price deviates significantly from daily VWAP (measured in ATR multiples) or RSI reaches extreme. Uses a layering (DCA-into-trade) approach — adds to the position at L2 and L3 deviation levels to lower average entry price.

## Entry Conditions
**Long (initial L1):**
- Price ≤ VWAP − (6.29 × ATR)  OR  RSI(26) ≤ 35.57

**Short (initial L1):**
- Price ≥ VWAP + (6.29 × ATR)  OR  RSI(26) ≥ 79.96

**Layering (ADD signals):**
- L2 add: price reaches VWAP ± (7.25 × ATR)
- L3 add: price reaches VWAP ± (1.50 × ATR) beyond L2

## Exit Conditions
- Take profit: 8.82% from average entry price OR price returns to VWAP (whichever is higher/lower)
- Stop loss: 8.66% from average entry price (intrabar check)

## Key Indicators
- VWAP — daily UTC reset anchor price
- ATR(13) — deviation band sizing
- RSI(26) — extreme zone entry trigger (oversold: 35.57, overbought: 79.96)

## Expected Edge
ETH tends to revert to VWAP on intraday timeframes after extreme deviations. Layering lowers average cost and improves TP hit rate, but increases exposure — hard SL prevents catastrophic loss.

## Data Requirements
- Columns needed: Close, High, Low, Volume
- Minimum timeframe: 1h
- Minimum history: 2 years

## Implementation Notes
- VWAP resets daily at UTC midnight — uses cumsum of (typical_price × volume) / cumsum(volume)
- Layering state is tracked per side (long/short) — resets after SL or TP
- Position qty drop detection handles post-liquidation resets cleanly

## Implementation Status: IMPLEMENTED

## Strategy Class
`ETHLayeredReversionStrategy` — `strategy_backtest/strategies/eth_layered_reversion_strategy.py`

---
## Connections

**Category:** [[Mean_Reversion/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260527_multi_tf_rsi_divergence]] · [[Mean_Reversion/20260527_keltner_rsi_reversion]] · [[Mean_Reversion/20260527_envelope_mean_reversion]] · [[Mean_Reversion/20260527_aroon_rsi_mean_reversion]] · [[Mean_Reversion/20260526_vwap_rsi_reversion]] · [[Mean_Reversion/20260526_tight_bollinger_scalper]]
