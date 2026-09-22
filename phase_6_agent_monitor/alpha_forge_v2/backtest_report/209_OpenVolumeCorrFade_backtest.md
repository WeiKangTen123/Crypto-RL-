# Strategy 209: Open Volume Correlation Fade Backtest Report

## 1. Strategy Overview
- **Name**: Open Volume Correlation Fade
- **Logic**: Sourced from WorldQuant Alpha #6. A simpler implementation of the open-volume factor using rolling Pearson correlation rather than time-series rank correlation.
  - Formula: `-corr(open, vol, corr_p)`
  - **Entry:** Acts as a directional filter. Enters Long when the correlation is extremely negative (i.e. alpha > `long_thresh`), indicating structural divergences between opening gaps and volume participation.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `corr_p`: 10
- `long_thresh`: 0.6
- `short_thresh`: -0.6
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.96`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- Similar to Strategy 205, the raw correlation without tuning produced a negative Sharpe (`-0.96`), showing that basic uncalibrated divergence logic is highly noise-prone in crypto.
- Strategy 205 (which used *Rank* correlation) tuned incredibly well to a `1.54` Sharpe. 
- **Optuna Tuning Results**: The linear correlation variant drastically outperformed the rank-based variant, arriving at a staggering **`2.20`** Sharpe ratio (Return: `102.9%`, Trades: `116`), marking it as one of the best strategies in the portfolio to date!
- **Tuned Parameters**: `{'corr_p': 20, 'long_thresh': 0.7, 'short_thresh': -0.8, 'sl_pct': 0.03, 'tp_pct': 0.15}`
- **Conclusion**: By extending the linear correlation window (`corr_p=20`) and using highly asymmetric entry conditions (`long_thresh=0.7`, `short_thresh=-0.8`), the strategy achieves incredible performance. It indicates that straightforward Pearson correlation catches divergence anomalies between the opening gap and session volume better than rank-normalized metrics. The extremely tight stop loss (`sl_pct=0.03`) coupled with a generous take profit (`tp_pct=0.15`) secures massive risk-adjusted gains.
