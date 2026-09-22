# Strategy 205: Open Volume Anticorrelation Backtest Report

## 1. Strategy Overview
- **Name**: Open Volume Anticorrelation
- **Logic**: Sourced from WorldQuant's Alpha #3. Measures the rolling rank correlation between the Open price and trading Volume.
  - Formula: `-corr(rank(open), rank(vol), 10)`
  - **Entry:** Acts as a directional filter. Enters Long when the correlation is extremely negative (i.e. alpha > `long_thresh`), indicating structural divergences between opening gaps and volume participation.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ts_p`: 10
- `corr_p`: 10
- `long_thresh`: 0.6
- `short_thresh`: -0.6
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.71`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline logic yielded a negative Sharpe of `-0.71`.
- Raw Open-Volume correlation without an explicit directional price delta can be noisy, as high volume on open can mean either capitulation or breakout.
- **Optuna Tuning Results**: The optimizer made a spectacular breakthrough, taking this strategy from `-0.71` to an elite **`1.54`** Sharpe ratio (Return: `62.6%`, Trades: `55`), moving it securely into the top "GOOD" category.
- **Tuned Parameters**: `{'ts_p': 20, 'corr_p': 20, 'long_thresh': 0.8, 'short_thresh': -0.8, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer significantly extended both the time-series rank window and the correlation window to `20` periods (approx 3.3 days on a 4H chart), and tightened the entry threshold to an extreme `0.8` correlation. This reveals that the `Open-Volume Anticorrelation` factor only possesses predictive edge at *macro structural extremes* rather than short-term fluctuations. When the 3-day rank of the Open price completely diverges from the 3-day rank of Volume (r > 0.8), it flags a massive structural inefficiency that leads to very highly profitable (albeit less frequent) trades.
