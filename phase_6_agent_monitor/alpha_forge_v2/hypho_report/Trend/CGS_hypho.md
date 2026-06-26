# Phase 6 Hypothesis Report: Choppiness-Gated Supertrend (CGS)

## Executive Summary
CGS addresses the primary weakness of the Supertrend indicator (whipsaw during ranges) by enforcing a strict mathematically-defined regime filter using the Choppiness Index (CHOP). 

## Mathematical Model
- **Supertrend Component**: Price > Upper Band (Long), Price < Lower Band (Short).
- **Gating Component**: Execute ONLY IF $\text{CHOP}_{14} < 38.2$.

## Regime Expectation
This strategy is highly selective. It expects to sit in CASH during extended sideways consolidation (which protects capital) and only deploys capital when a volatility expansion forces CHOP below the 38.2 threshold.

## Risk Profile
- **Holding Period**: 3 to 7 days (Macro Swings).
- **Poison Filter Validation**: Explicitly rectifies the failures of `SupertrendProStrategy` logged in the system autopsies.
