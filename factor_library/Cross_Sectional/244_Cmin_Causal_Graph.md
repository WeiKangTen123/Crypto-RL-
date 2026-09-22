---
tags: [factor_card, Cross_Sectional, status/VALIDATED]
aliases: [Strategy_244_Cmin Causal Graph]
---
# Alpha Card: Cmin Causal Graph

## 1. Mathematical Core
- **Concept:** Dynamically calculates the causal information flow (lagged cross-correlation) between all coins to build a directed causal graph (DAG proxy). Trades Follower coins when the Market Leader surges.
- **Implementation Path:** Native python class implementation overriding `generate_signals()`.

## 2. Theoretical Justification
- **Why it works:** By operating outside the standard bounds of simple moving averages, this mathematical structure aims to exploit deep structural inefficiencies or capitulations in the 4H timeframe.
- **Risk:** High parameter sensitivity due to complex math.

## 3. Implementation Plan
- **Stage 1 (Ingest):** Code mathematical functions.
- **Stage 2 (Build):** Embed into strategy class with tunable Optuna boundaries.
- **Stage 3 (Test):** Reject if Sharpe < 1.0 (unless explicitly retained for correlation).
