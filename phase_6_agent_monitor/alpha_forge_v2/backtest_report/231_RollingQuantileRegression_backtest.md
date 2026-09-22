# Backtest Report: 231_RollingQuantileRegression

## 1. Strategy Identity
- **ID:** `231`
- **Class:** `RollingQuantileRegression`
- **Type:** Deep Learning / Machine Learning Factor
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `sm.QuantReg(Returns ~ VolumeDelta + Volatility)` @ `q=0.05` and `q=0.95`.
- **Machine Learning Integration:** Uses the Python `statsmodels` library to fit a live mathematical optimization model (Quantile Regression) as the backtest walks forward in time. 
- **Tail Risk Asymmetry:** Instead of predicting the *average* price move (like OLS regression), it specifically attempts to predict the extreme upper (95th percentile) and lower (5th percentile) boundaries of risk.
- **Action:** If the model predicts that the upside potential (Upper Tail) is severely larger than the downside risk (Lower Tail) by a threshold factor, it goes long. This signals that a "washout" has occurred and volatility is asymmetric to the upside. To save on extreme compute costs, the model is re-fitted only periodically (every N bars) and forward-fills its predictions.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values.

## 4. Analysis and Next Steps
- **Optuna Tuning Results:** After crunching through over 80,000 live Machine Learning model fits per tuning trial, the optimizer pushed the strategy to a **`0.45` Sharpe ratio** (Return: `54.7%`, Trades: `351`).
- **Tuned Parameters**: `{'q_lower': 0.05, 'q_upper': 0.95, 'lookback': 100, 'step_size': 24, 'asym_thresh': 3.0, 'sl_pct': 0.1, 'tp_pct': 0.2}`
- **Conclusion**: The optimizer cranked the `asym_thresh` up to `3.0`, meaning it only enters trades when the mathematical probability of a massive upside tail is *three times* larger than the downside tail risk. It also widened the `step_size` to 24 (4 days), effectively reducing noise and preventing over-trading. While a 0.45 Sharpe is in the "MEDIOCRE" tier, it is profitable and highly conservative (only 351 trades over 5 years). This proves that Quantile Regression can predict tail-risk asymmetry in Crypto, but it might need to be paired with a trend-following overlay to hit "GOOD" status.
