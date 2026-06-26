# Phase 6 Hypothesis Report: Hidden Markov Model (HMM) Regime Classifier

## Executive Summary
Financial markets exhibit non-stationary behaviors where statistical properties like mean and volatility shift dynamically across distinct market regimes (e.g., quiet trends, sideways chop, or panic sell-offs). The Hidden Markov Model (HMM) Regime Classifier addresses this by modeling the market as a sequence of unobservable (hidden) states. It uses observable variables (log returns and normalized volatility) to statistically decode the current market regime, acting as an adaptive gating filter. By identifying and filtering out sideways chop regimes, the system prevents whipsawing and toggles appropriate entry logic for bullish and bearish trends.

## Mathematical Model
- **Feature Computation**:
  - Log Returns:
    $$r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$
  - Normalized Volatility (using ATR):
    $$\text{NormVol}_t = \frac{\text{ATR}_t(\text{period}=14)}{P_t}$$
  - Feature Matrix:
    $$\mathbf{X} = [r_t, \text{NormVol}_t]^T$$
- **HMM Transition & Emission Dynamics**:
  - Hidden states $S_t \in \{0, 1, 2\}$, where state transitions are governed by the probability matrix $\mathbf{A} = \{a_{ij}\}$ where $a_{ij} = P(S_t = j \mid S_{t-1} = i)$.
  - Observed features $\mathbf{X}_t$ given state $s$ follow Gaussian emission distributions:
    $$P(\mathbf{X}_t \mid S_t = s) \sim \mathcal{N}(\boldsymbol{\mu}_s, \boldsymbol{\Sigma}_s)$$
- **Decoding and Posterior Probability Gating**:
  - Decoding is performed using the Viterbi algorithm to find the most likely sequence of states, or by computing posterior probability distributions:
    $$\gamma_t(s) = P(S_t = s \mid \mathbf{X}_{1:t})$$
  - Gated Entry: An entry is permitted only if the maximum posterior probability exceeds a high-confidence threshold:
    $$\max_s \gamma_t(s) \ge 0.60$$
- **State Sorting Constraint**:
  - To resolve the label-switching problem during fitting, states are sorted ascendingly by their return mean ($\mu_{r}$):
    - **State 0 (Bearish/Volatile)**: Max negative log return mean.
    - **State 1 (Sideways Chop)**: Near-zero log return mean.
    - **State 2 (Bullish/Steady)**: Max positive log return mean.

## Regime Expectation
This classifier expects to segment the market into three clear operational states. In trend-following environments, the HMM will classify the market into either the Bullish (State 2) or Bearish (State 0) regime, enabling clean momentum capturing. During periods of consolidation, the HMM decodes State 1 (Sideways Chop), triggering a macro gate that halts all trend entries and exits active positions to preserve capital.

## Risk Profile
- **Holding Period**: Short-to-medium-term (typically 1 to 5 days, aligning with 4h and 1h primary timeframes).
- **Poison Filter Validation**: Explicitly bypasses the whipsaw vulnerability of un-gated trend strategies by utilizing HMM state gating. This directly addresses the performance failures of simple trend-following strategies (such as `EMACrossoverStrategy` and `SupertrendProStrategy`) documented in the system autopsies.
- **Strategic Disadvantages**:
  - *Lagging State Transitions*: The model relies on rolling historical observations and may lag during abrupt state shifts (e.g., sudden flash crashes).
  - *Estimation Instability*: Unnormalized inputs or insufficient historical training windows (window < 2000) can cause the EM solver to fail to converge or overfit noise.
