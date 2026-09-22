# Strategy 212: Close Delta Conditional Flip Backtest Report

## 1. Strategy Overview
- **Name**: Close Delta Conditional Flip
- **Logic**: Sourced from WorldQuant Alpha #9.
  - Formula: `((ts_min(delta(close, 1), 5) > 0) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))`
  - **Entry:** Acts as a trend filter. If the asset is in a pure up-trend (5-period min delta is > 0) or pure down-trend (5-period max delta < 0), it goes with the momentum (alpha = delta). Otherwise, it assumes the asset is ranging and fades the momentum (alpha = -delta). We divide alpha by close price to normalize it across assets.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `delta_p`: 1
- `ts_p`: 5
- `long_thresh`: 0.01
- `short_thresh`: -0.01
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.74`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.74`. 
- Pure trend-momentum vs range-fade is a sound logic for crypto, but the baseline parameters are far too tight (`delta_p=1`, `ts_p=5`). 
- **Optuna Tuning Results**: The optimizer improved the strategy to a **`0.61`** Sharpe ratio (Return: `31.0%`, Trades: `392`), classifying it as "MEDIOCRE".
- **Tuned Parameters**: `{'delta_p': 1, 'ts_p': 3, 'long_thresh': 0.03, 'short_thresh': -0.03, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: By shortening the trend-identification lookback to just 3 periods (`ts_p=3`) and raising the threshold to require larger raw price gaps (`long_thresh=0.03`), the optimizer managed to turn the severe negative baseline into a slightly positive edge. However, trading raw price deltas directly (even conditionally) remains highly volatile. Strategy 213 applies a rank normalization to this exact logic, which may stabilize the signal further.
