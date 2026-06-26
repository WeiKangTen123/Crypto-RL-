---
coins: BTC, ETH, BNB, SOL, XRP
directional_bias: Symmetric
factor_class: Trend_Momentum
interest: High
max_drawdown: 0.0
name: Lorentzian Classification Momentum
optimal_regime: Trend
sharpe: 0.0
source: TradingView PineScript
status: IN_PROGRESS
strategy_id: TBD
tags:
- alpha
- factor
- Trend_Momentum
- machine-learning
- knn
- lorentzian
- in_progress
timeframes: 1h, 4h
total_return: 0.0
type: short-term
win_rate: 0.0
---
# Lorentzian Classification Momentum

## Concept
Lorentzian distance is a distance metric that is inherently robust to outliers, unlike the standard Euclidean distance. By calculating the Lorentzian distance between the current market state (defined by features like RSI, CCI, and ADX) and historical states, we can classify the current price action as bullish or bearish based on its nearest historical neighbors. This exploits the repeating fractal nature of markets while filtering out the noisy, extreme volatility spikes (fat-tail events) that typically distort traditional ML clustering algorithms in crypto.

## Agent Reasoning (Chain of Thought)
Discovered during STAGE 1 Web Search via a prominent MachineLearning Pine Script. The factor was selected because it successfully applies a non-Euclidean distance metric to smooth out crypto's inherent noise. The engineering decision focuses on adapting this into a K-Nearest Neighbors (KNN) approximation using RSI, CCI, and ADX as the primary feature vectors to avoid overfitting. The core math relies on the Lorentzian metric $\sum \ln(1 + |x_i - y_i|)$ for neighbor selection.

## Market Regime
- **Works best in**: Trend-following environments / Structural shifts
- **Breaks down in**: Low-volatility chop where historical nearest neighbors offer conflicting signals
- **Suggested regime filter**: ADX(14) > 20 to ensure sufficient trend strength before querying the classification model.

## Strategy Play Style
This is an adaptive, dynamic momentum strategy that plays like a real-time pattern matcher. It dynamically shifts its bias by continually querying the K-nearest historical states. It relies on mathematical pattern recognition rather than fixed threshold crossovers, making it a "reactive trend-follower" that constantly adapts to the nearest historical precedent.

## Strategic Disadvantages
1. **Computational Cost**: High processing overhead if the historical lookup window is too large.
2. **Regime Shift Vulnerability**: Susceptible to structural regime changes where historical patterns (e.g., from a low-liquidity era) are no longer valid for the current market state.
3. **Exogenous Shocks**: Can lag during sudden, unprecedented news-driven events since it needs a historical precedent to classify correctly.

## Enhancement Recommendations
1. **Rolling History Window**: Limit the nearest-neighbor lookup to a rolling window (e.g., the last 2000 bars) to ensure pattern relevance.
2. **Confidence Threshold**: Implement an execution filter that only takes trades when the "confidence" (agreement among the K nearest neighbors) exceeds a certain threshold (e.g., 4 out of 5 neighbors agree).
3. **Time-Weighted Decay**: Assign a decay factor so more recent historical matches are weighted higher than older ones.

## Entry Logic
- **Long**: Lorentzian KNN prediction sum is $\ge +3$ (Bullish majority) AND Close > EMA(200) AND ADX(14) > 20.
- **Short**: Lorentzian KNN prediction sum is $\le -3$ (Bearish majority) AND Close < EMA(200) AND ADX(14) > 20.

## Exit Logic
- **Take Profit**: 2.0× ATR trailing stop, or a reverse signal classification flip.
- **Stop Loss**: 1.0× ATR below entry low.
- **Default R:R**: 2:1

## Signal Logic (Pseudocode)
```python
# Step 1 — Compute features
rsi = calc_rsi(close, 14)
cci = calc_cci(high, low, close, 14)
adx = calc_adx(high, low, close, 14)
ema_200 = calc_ema(close, 200)

current_vector = [rsi[-1], cci[-1], adx[-1]]

# Step 2 — Lorentzian Distance Function
def lorentzian_distance(x, y):
    return sum(np.log(1 + abs(x_i - y_i)) for x_i, y_i in zip(x, y))

# Step 3 — K-Nearest Neighbors Classification (K=5)
distances = [lorentzian_distance(current_vector, hist_vector) for hist_vector in rolling_history]
k_nearest_indices = argsort(distances)[:5]
prediction_score = sum(historical_labels[i] for i in k_nearest_indices) # labels are +1 or -1

# Step 4 — Entry signals
long_signal = (prediction_score >= 3) AND (close > ema_200[-1]) AND (adx[-1] > 20)
short_signal = (prediction_score <= -3) AND (close < ema_200[-1]) AND (adx[-1] > 20)

# Step 5 — Exit
tp_long = entry_price + 2.0 * atr[-1]
sl_long = entry_price - 1.0 * atr[-1]
```

## Key Indicators & Default Parameters
| Indicator | Default Params | library.py Function |
|---|---|---|
| RSI | period=14 | `calc_rsi(df, 14)` |
| CCI | period=14 | `calc_cci(df, 14)` |
| ADX | period=14 | `calc_adx(df, 14)` |
| EMA | period=200 | `calc_ema(df, 200)` |
| Lorentzian KNN | K=5, History=2000 | TBD in `library.py` (e.g., `calc_lorentzian_classification(df, K=5)`) |

## Recommended Logic Switches (For @alpha-developer)
- `entry_filter`: ['NONE', 'ADX_ABOVE_20', 'EMA_TREND_FILTER']
- `exit_mode`: ['FIXED_TP_SL', 'ATR_TRAILING_STOP', 'CLASSIFICATION_FLIP']
- `k_neighbors`: [3, 5, 7]

## Data Requirements
### Available Binance Columns
| Column | Parquet Path | Used For |
|---|---|---|
| `Open`, `High`, `Low`, `Close` | `dataset/{COIN}/{TF}/spot_ohlcv.parquet` | Price action, indicators |
| `Volume` | same | Volume filter |

## Implementation
- Minimum timeframe: 1h
- Minimum history: 2000 bars
- Library function: `strategy_backtest/library.py` → `calc_lorentzian_classification`

## Observations & Wisdom
- Integrating distance metrics typically demands robust normalization of the input features to ensure RSI, CCI, and ADX contribute equally to the distance calculation without dominating due to arbitrary scale differences.

## Connections
**Category:** [[Trend_Momentum/_Index]]
**Indicators:** [[_Concepts/RSI]] · [[_Concepts/EMA]]
**Related Factors:** [[_Concepts/Order_Flow]]
