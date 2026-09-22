---
tags: [factor_card, Cross_Sectional, status/VALIDATED]
aliases: [Strategy_245_Capm Alpha Separation]
---
# Alpha Card: Capm Alpha Separation

## 1. Mathematical Core
- **Concept:** Calculates the rolling Beta of an Altcoin against BTC to extract its idiosyncratic Alpha Residual. Trades when the Alpha Residual surges, indicating true fundamental breakout independent of macro flows.
- **Implementation Path:** Native python class implementation overriding `generate_signals()`.

## 2. Theoretical Justification
- **Why it works:** By operating outside the standard bounds of simple moving averages, this mathematical structure aims to exploit deep structural inefficiencies or capitulations in the 4H timeframe.
- **Risk:** High parameter sensitivity due to complex math.

## 3. Implementation Plan
- **Stage 1 (Ingest):** Code mathematical functions.
- **Stage 2 (Build):** Embed into strategy class with tunable Optuna boundaries.
- **Stage 3 (Test):** Reject if Sharpe < 1.0 (unless explicitly retained for correlation).
