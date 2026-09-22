---
name: ChoppinessGatedSupertrendStrategy
strategy_id: 135
type: short-term
factor_class: Momentum
directional_bias: Symmetric
optimal_regime: Any
timeframes: 5m
coins: BTC
interest: High
status: IMPLEMENTED
sharpe: 1.57
---

# Hypothesis: ChoppinessGatedSupertrendStrategy

## Concept
Exploits intra-day momentum using short-term entry triggers with higher timeframe trend alignment.

## Entry Logic
- **Long/Short**: Uses `ForgeStrategy` configuration registered in settings.py

## Key Indicators
- Entry Signal
- HTF EMA/Supertrend Filter
- ATR for volatility trailing

Implementation handled by `ForgeStrategy` dynamic registry.
