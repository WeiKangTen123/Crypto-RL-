---
coins: BTC, ETH, SOL
interest: High
name: adaptive-freqai-momentum
source: GitHub (freqtrade/freqai)
status: QUEUED
tags:
- queued
timeframes: 1h, 4h
type: short-term
---
# Adaptive Momentum with FreqAI

## Concept
Uses machine learning (XGBoost or LightGBM) to predict price movements based on a large set of technical indicators (20+). The model is retrained periodically to adapt to changing market regimes. It exploits non-linear relationships between indicators and future price action.

## Entry Conditions
- Model predicts positive return > threshold.
- Probability/Confidence score > 0.6.
- Optional: Trend filter (EMA 200).

## Exit Conditions
- Take profit: Dynamic based on predicted volatility or fixed percentage.
- Stop loss: Dynamic based on ATR or fixed percentage.
- Time-based exit: If the prediction horizon is reached.

## Key Indicators
- RSI, MACD, Bollinger Bands, EMA, Volume, Taker Buy/Sell ratio.
- Target: N-period future return.

## Expected Edge
Machine learning can capture complex patterns that simple rule-based strategies miss, especially in high-noise crypto markets. Periodic retraining handles regime shifts.

## Data Requirements
- Columns needed: Open, High, Low, Close, Volume, taker_buy_base_vol, num_trades.
- Minimum timeframe: 1h
- Minimum history: 2 years (for training/validation).

## Implementation Notes
- Requires integration with a ML library (scikit-learn, xgboost).
- Need to handle feature scaling and lagging.
- Backtesting requires a walk-forward approach or "Purged K-Fold" to avoid leakage.

---
## Connections

**Category:** [[Trend_Momentum/_Index]]

**Indicators:** [[_Concepts/ATR]] · [[_Concepts/EMA]] · [[_Concepts/RSI]]

**Related Factors:** [[Mean_Reversion/20260528_golden_zone_fib_bos]] · [[Mean_Reversion/20260527_z_score_stat_arb]] · [[Mean_Reversion/20260527_fisher_transform_reversal]] · [[Mean_Reversion/20260527_dump_reversal]] · [[Mean_Reversion/20260527_Order_Block_SMC_Reversal]] · [[Mean_Reversion/20260526_liquidity_sweep_reversal]]
