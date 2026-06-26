# Hypothesis Report: Adaptive Volatility Squeeze (AVS)

## Executive Summary
This strategy attempts to capture multi-day volatility expansions in major crypto assets following periods of low-volatility consolidation. It specifically targets Medium Frequency Trading (MFT) metrics on the 4h timeframe, aiming for a 2-3% monthly ROI (~25% MDD) by utilizing Bollinger/Keltner squeezes gated by ADX trend-exhaustion and confirmed by Fisher Transform momentum.

## Mathematical Model
1.  **Regime Filter**: `calc_adx < 25` ensures the market is in a structural consolidation.
2.  **Squeeze Energy**: `calc_bb_kc_squeeze` validates that Bollinger Bands are within Keltner Channels.
3.  **Breakout Trigger**: A breakout is registered when the squeeze releases AND `calc_fisher_transform` confirms the directional momentum (Fisher crosses trigger line).
4.  **Risk Management**: `calc_chandelier_exit` provides a dynamic trailing stop to capture multi-day runs while capping the downside.

## Regime Expectation
-   **Optimal Environment**: Late-stage consolidations in trending macro environments.
-   **Hostile Environment**: High-volatility chop where false breakouts occur.

## Risk Profile
-   **Target Sharpe**: 1.0 - 1.5
-   **Target MDD**: ~25%
-   **Trade Frequency**: 1-3 times per week across 5 major coins.
