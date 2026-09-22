---
tags: [factor_card, Trend_Momentum, status/VALIDATED]
aliases: [Strategy_242_Walk-Forward RF]
---
# Alpha Card: Walk-Forward RF

## 1. Mathematical Core
- **Concept:** A rolling time-series Machine Learning model (Random Forest) that retrains itself every 33 days to predict forward returns using non-linear structural features (SHAP proxy).
- **Implementation Path:** Native python class implementation overriding `generate_signals()`.

## 2. Theoretical Justification
- **Why it works:** By operating outside the standard bounds of simple moving averages, this mathematical structure aims to exploit deep structural inefficiencies or capitulations in the 4H timeframe.
- **Risk:** High parameter sensitivity due to complex math.

## 3. Implementation Plan
- **Stage 1 (Ingest):** Code mathematical functions.
- **Stage 2 (Build):** Embed into strategy class with tunable Optuna boundaries.
- **Stage 3 (Test):** Reject if Sharpe < 1.0 (unless explicitly retained for correlation).
