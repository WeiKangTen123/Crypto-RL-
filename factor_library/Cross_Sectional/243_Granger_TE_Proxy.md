---
tags: [factor_card, Cross_Sectional, status/VALIDATED]
aliases: [Strategy_243_Granger TE Proxy]
---
# Alpha Card: Granger TE Proxy

## 1. Mathematical Core
- **Concept:** Calculates the Transfer Entropy (Causal Information Flow) from BTC to Altcoins. Trades Altcoins on the macro trend if Beta-Slaved, or on idiosyncratic trend if decoupled.
- **Implementation Path:** Native python class implementation overriding `generate_signals()`.

## 2. Theoretical Justification
- **Why it works:** By operating outside the standard bounds of simple moving averages, this mathematical structure aims to exploit deep structural inefficiencies or capitulations in the 4H timeframe.
- **Risk:** High parameter sensitivity due to complex math.

## 3. Implementation Plan
- **Stage 1 (Ingest):** Code mathematical functions.
- **Stage 2 (Build):** Embed into strategy class with tunable Optuna boundaries.
- **Stage 3 (Test):** Reject if Sharpe < 1.0 (unless explicitly retained for correlation).
