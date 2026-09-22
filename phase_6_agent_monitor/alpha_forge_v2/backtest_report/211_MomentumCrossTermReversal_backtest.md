# Strategy 211: Momentum Cross Term Reversal Backtest Report

## 1. Strategy Overview
- **Name**: Momentum Cross Term Reversal
- **Logic**: Sourced from WorldQuant Alpha #8.
  - Formula: `-1 * rank(2 * rank(correlation(ts_rank(close, 10), ts_rank(volume, 10), 10)) - rank(delta(close, 10)))`
  - **Entry:** A highly nested factor that combines the momentum of the close price (rank of delta) with the rolling correlation of price and volume ranks. A high alpha implies the price is dropping while the correlation of price/volume ranks is low (or inverse).
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ts_p`: 10
- `corr_p`: 10
- `delta_p`: 10
- `rank_p`: 10
- `long_thresh`: -0.2
- `short_thresh`: -0.8
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.35`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.35`.
- **Optuna Tuning Results**: The optimizer made a fantastic discovery, bringing this highly complex factor up to a **`0.93`** Sharpe ratio (Return: `42.6%`, Trades: `518`), placing it securely in the "GOOD" category.
- **Tuned Parameters**: `{'ts_p': 10, 'corr_p': 5, 'delta_p': 5, 'rank_p': 20, 'long_thresh': -0.2, 'short_thresh': -0.8, 'sl_pct': 0.05, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer squeezed edge out of this convoluted formula by making the cross-term variables highly reactive (`corr_p=5`, `delta_p=5`), while extending the final smoothing rank window (`rank_p=20`). This means the strategy tracks rapid 20-hour momentum and correlation shifts, but evaluates them against a longer 3-day baseline to decide if the reversal signal is genuine. The fact that a mathematical formula this nested produced a near-1.0 Sharpe indicates that complex multi-term interactions *can* work when properly timescale-aligned.
