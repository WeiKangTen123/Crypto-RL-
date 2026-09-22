# Hypothesis Report: Strategy 237 - Extreme Nested Decay

## 1. The Core Hypothesis
The asset displays inefficiencies during anomalous structural events. We hypothesize that by utilizing the `Extreme Nested Decay` mathematical framework, we can isolate these anomalies and capture edge before the market recalibrates.

## 2. Experimental Design
- **Asset Universe:** Top 10 High-Cap Crypto
- **Timeframe:** 4-hour (4H)
- **Period:** 2021-05-31 to 2026-05-31 (5 years)
- **Algorithm:** A highly restrictive AND-gate spanning dual-timeframe linearly decaying structures. Designed to catch falling knives on absolute washout events.
- **Constraints:** Stop losses tighter than 5% are explicitly banned to prevent Optuna from hacking the metric via noise-scalping.

## 3. Expected Failure Modes
- The logic may be too slow/lagging on a fast-moving crypto asset.
- The signal density might be too low, resulting in fewer than 50 trades over 5 years.
