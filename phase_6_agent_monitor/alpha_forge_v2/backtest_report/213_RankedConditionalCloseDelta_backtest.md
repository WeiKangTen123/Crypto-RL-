# Strategy 213: Ranked Conditional Close Delta Backtest Report

## 1. Strategy Overview
- **Name**: Ranked Conditional Close Delta
- **Logic**: Sourced from WorldQuant Alpha #10.
  - Formula: `rank(((ts_min(delta(close, 1), 4) > 0) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))`
  - **Entry:** This is the exact same logic as Strategy 212, but wrapped in a time-series rank to normalize the output bounded between 0 and 1. 
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `delta_p`: 1
- `ts_p`: 4
- `rank_p`: 10
- `long_thresh`: 0.7
- `short_thresh`: 0.3
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.44`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.44`. Wrapping the raw delta in a rank did improve the baseline compared to Strategy 212 (`-0.74`), proving that normalization helps.
- **Optuna Tuning Results**: The optimizer improved the strategy to a **`0.51`** Sharpe ratio (Return: `43.9%`, Trades: `331`), classifying it as "MEDIOCRE".
- **Tuned Parameters**: `{'delta_p': 2, 'ts_p': 3, 'rank_p': 5, 'long_thresh': 0.7, 'short_thresh': 0.2, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer shortened the trend lookback (`ts_p=3`) and the rank window (`rank_p=5`), but slightly widened the delta measurement to 2 periods (`delta_p=2`). It essentially created a hyper-reactive local momentum rank. The result is positive, but still heavily reliant on stop losses and take profits rather than a strong directional edge.
