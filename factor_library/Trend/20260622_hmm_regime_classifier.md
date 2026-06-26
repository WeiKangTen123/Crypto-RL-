---
name: Hidden Markov Model (HMM) Regime Classifier
strategy_id: TBD
type: short-term
factor_class: Trend
directional_bias: Symmetric
optimal_regime: Any
timeframes: 4h, 1h, 1d
coins: BTC, ETH, BNB, SOL, XRP
source: arXiv, GitHub
interest: High
status: QUEUED
sharpe: 0.0
win_rate: 0.0
total_return: 0.0
max_drawdown: 0.0
tags: [alpha, factor, Trend, machine-learning, regime-classification, hmm]
---

# Hidden Markov Model (HMM) Regime Classifier

## Concept
Financial time series are non-stationary, meaning their statistical properties (mean, variance) shift over time as the market transitions between different structural regimes (e.g., quiet trending, high-volatility sideways, panic sell-offs). A Hidden Markov Model (HMM) models the market as an unobservable (hidden) sequence of discrete states, where the observed market data (log returns and normalized volatility) are drawn from probability distributions linked to the active state. By fitting an HMM to historical data, we can statistically identify these hidden regimes and compute the probability of being in each regime. This exploits the tendency of market volatility and trend regimes to persist (cluster) over time, allowing us to dynamically scale positions, adjust stop losses, or toggle strategy logic (e.g., trend-following vs. mean-reversion) to match the current regime.

## Agent Reasoning (Chain of Thought)
Discovered during STAGE 1 Web Search via academic papers on explainable cryptocurrency microstructure and HMM regime segmentation. Traditional trading strategies fail when their fixed parameters (e.g., moving average windows or RSI thresholds) are applied across changing market states. By utilizing a 3-state HMM trained on historical log returns and normalized ATR volatility, we can classify the market into discrete states (Bullish Trend, Bearish Trend, Sideways Chop). This acts as a macro gate filter: when the model detects a Sideways Chop regime, trend-following logic is disabled to avoid whipsaws. The core math utilizes Gaussian emissions, trained via the Baum-Welch (EM) algorithm, and decoded via the Viterbi algorithm or forward posterior probability calculation.

## Market Regime
- **Works best in**: Multi-state transitions where distinct structural regimes (e.g., quiet accumulation vs. momentum breakouts vs. high-volatility panics) occur sequentially.
- **Breaks down in**: High-frequency mean-reverting regimes that switch states faster than the historical observation window can adapt, causing lagging classifications.
- **Suggested regime filter**: HMM Posterior Probability > 0.60 to confirm high-confidence state assignment before signaling.

## Entry Logic
- **Long (Regime 1 - Bullish Trend)**: Enter long when HMM decodes state as Regime 1 (characterized by positive mean returns and low-to-moderate volatility) AND Close > EMA(50).
- **Short (Regime 2 - Bearish Trend)**: Enter short when HMM decodes state as Regime 2 (characterized by negative mean returns and high volatility) AND Close < EMA(50).
- **No Trade / Exit (Regime 0 - Sideways Chop)**: Disable all entries and exit existing trades when the most likely state is decoded as Regime 0 (characterized by near-zero mean returns and low volatility).

## Exit Logic
- **Take Profit**: 2.5× ATR trailing stop, or exit immediately when a regime transition to a conflicting state occurs.
- **Stop Loss**: 1.5× ATR below entry low or when the probability of the active regime falls below 40%.
- **Default R:R**: 2:1 (adapted to regime-based targets).

## Signal Logic (Pseudocode)
```python
# Step 1 — Compute features (Log Returns & Normalized Volatility)
log_returns = np.log(close / shift(close, 1))
norm_volatility = ATR(high, low, close, 14) / close

# Feature matrix
X = np.column_stack([log_returns, norm_volatility])

# Step 2 — Hidden Markov Model (N_states=3, trained via Baum-Welch)
# Transition probability matrix (A) and Gaussian Emission params (mu, sigma) are loaded/updated
# In backtest: we fit model on rolling training window (e.g., last 2000 bars)
# and predict current hidden state via Viterbi decoding or calculate posteriors:
state_probabilities = calc_hmm_posteriors(X, n_states=3)
current_state = np.argmax(state_probabilities[-1])

# Map states based on mean of log_returns:
# State with max positive return mean = Bullish (Regime 1)
# State with max negative return mean = Bearish (Regime 2)
# State with return mean close to 0 = Sideways (Regime 0)

bullish_state_id = get_state_id_with_highest_mean(returns_means)
bearish_state_id = get_state_id_with_lowest_mean(returns_means)
sideways_state_id = get_remaining_state_id()

# Step 3 — Entry signals
long_signal  = (current_state == bullish_state_id) AND (close > EMA(close, 50))
short_signal = (current_state == bearish_state_id) AND (close < EMA(close, 50))

# Step 4 — Exit / Flat regime
flat_regime_signal = (current_state == sideways_state_id)
```

## Key Indicators & Default Parameters
| Indicator | Default Params | library.py Function |
|---|---|---|
| HMM Classifier | n_states=3, covariance_type='full', window=2000 | `calc_hmm_regime_classifier(df, n_states=3, window=2000)` |
| ATR | period=14 | `calc_atr(df, 14)` |
| EMA | period=50 | `calc_ema(df, 50)` |

## Recommended Logic Switches (For @alpha-developer)
- `regime_mode`: ['3_STATE_GAUSSIAN', '2_STATE_GAUSSIAN']
- `feature_selection`: ['RETURNS_ONLY', 'RETURNS_VOLATILITY', 'RETURNS_VOLATILITY_VOLUME']
- `entry_gating`: ['STRICT_VITERBI', 'POSTERIOR_THRESHOLD_60', 'NONE']

## Data Requirements
### Available Binance Columns
| Column | Parquet Path | Used For |
|---|---|---|
| `Open`, `High`, `Low`, `Close` | `dataset/{COIN}/{TF}/spot_ohlcv.parquet` | Price action, Log returns |
| `Volume` | same | Optional Volume feature |
| `Volume` | same | Volatility calculation (ATR) |

## Institutional Guards
- **Data Quality Constraint**: Memory logs indicate widespread stale data and anomalies across lower timeframes (e.g., `1m`, `5m`, `15m`) for major pairs (`BTC`, `ETH`, `BNB`, `SOL`, `XRP`). Therefore, HMM fitting and decoding MUST strictly run on robust timeframes (`4h` primary, `1h` secondary) to prevent optimization crashes and noisy emissions.
- **Poison Control**: As per the `AVOID_FACTOR_CLASS` constraint, do not combine this factor with simple trend-following strategies without gating. It must be implemented strictly as a regime filter/gate.
- **Library-First Mandate**: The HMM fitting, Gaussian emission estimation, and state decoding algorithms must be implemented as a pure, standalone function `calc_hmm_regime_classifier` in `strategy_backtest/library.py`.

## Strategy Play Style
Regime-Aware Trend/Reversion Switching. It acts as an adaptive filter that determines the market environment type before allocating capital.

## Strategic Disadvantages
1. **Lagging State Transitions**: HMM is historical and can lag at transition points, temporarily keeping the strategy in a trend-following state during a sudden flash crash or chop phase.
2. **State Swapping/Label Switching**: During estimation, state labels (e.g., State 0, 1, 2) can swap randomly unless they are programmatically sorted by their parameter means (e.g., ascending log return means).
3. **Overfitting**: Choosing too many states (e.g., N > 3) or too many features can cause the Baum-Welch solver to overfit local noise, rendering out-of-sample predictions useless.

## Enhancement Recommendations
1. **State Sorting**: Sort states by log return mean so State 0 is always lowest (bearish/volatile), State 1 is moderate (sideways), State 2 is highest (bullish/steady).
2. **Transition Probability Smoothing**: Apply Dirichlet priors or smoothing constraints on the transition matrix to prevent rapid state oscillation (flickering).
3. **Adaptive Windowing**: Dynamically scale the training window size based on market volatility to speed up transition response.

## Performance Summary
*Auto-updated by `sync_backtest_to_obsidian.py` when `strategy_id` matches.*

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.0 |
| Win Rate | 0.0% |
| Total Return | 0.0% |
| Max Drawdown | 0.0% |

## Observations & Wisdom
- Hidden Markov Models offer mathematical rigor for regime classification, but the quality of output is highly sensitive to feature scaling and normalization.

## Connections
**Category:** [[Trend/_Index]]
**Indicators:** [[_Concepts/ATR]]
**Related Factors:** [[factor_library/Trend/CGS_card.md]]
