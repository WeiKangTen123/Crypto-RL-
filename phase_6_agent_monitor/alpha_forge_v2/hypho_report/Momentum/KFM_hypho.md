# Phase 6 Hypothesis Report: Kalman Filtered Momentum (KFM)

## Executive Summary
KFM is an advanced MFT strategy designed to track latent price states using a Kalman Filter. By filtering out transient 4H noise, it captures sustained multi-day momentum shifts.

## Mathematical Model
- **Latent State Estimation**: $x_t = x_{t-1} + w_t$
- **Measurement Equation**: $z_t = x_t + v_t$
- **Signal Generation**: Long when $\Delta x_t > \text{threshold}$. Short when $\Delta x_t < -\text{threshold}$.

## Regime Expectation
Designed specifically for high-volatility, high-trend regimes (e.g., late-stage bull markets or capitulation sell-offs).

## Risk Profile
- **Holding Period**: 2 to 5 days.
- **Drawdown Protection**: Requires trailing Chandelier Exit to protect unrealized gains against flash-crashes.
