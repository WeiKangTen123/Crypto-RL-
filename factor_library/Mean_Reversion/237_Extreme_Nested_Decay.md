---
tags: [factor_card, Mean_Reversion, status/VALIDATED]
aliases: [Strategy_237_Extreme Nested Decay]
---
# Alpha Card: Extreme Nested Decay

## 1. Mathematical Core
- **Concept:** A highly restrictive AND-gate spanning dual-timeframe linearly decaying structures. Designed to catch falling knives on absolute washout events.
- **Implementation Path:** Native python class implementation overriding `generate_signals()`.

## 2. Theoretical Justification
- **Why it works:** By operating outside the standard bounds of simple moving averages, this mathematical structure aims to exploit deep structural inefficiencies or capitulations in the 4H timeframe.
- **Risk:** High parameter sensitivity due to complex math.

## 3. Implementation Plan
- **Stage 1 (Ingest):** Code mathematical functions.
- **Stage 2 (Build):** Embed into strategy class with tunable Optuna boundaries.
- **Stage 3 (Test):** Reject if Sharpe < 1.0 (unless explicitly retained for correlation).
