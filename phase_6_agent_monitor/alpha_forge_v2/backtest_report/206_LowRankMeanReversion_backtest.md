# Strategy 206: Low Rank Mean Reversion Backtest Report

## 1. Strategy Overview
- **Name**: Low Rank Mean Reversion
- **Logic**: Sourced from WorldQuant Alpha #4. A pure time-series mean-reversion factor based on the relative position of the Low price.
  - Formula: `-ts_rank(Low, ts_period)`
  - **Entry:** We enter Long when the current Low is near the lowest point of the trailing window (alpha > `long_thresh`), expecting an oversold bounce. We Short when the current Low is the highest of the trailing window (alpha < `short_thresh`), expecting an overbought pullback.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ts_period`: 9
- `long_thresh`: -0.2
- `short_thresh`: -0.8
- `sl_pct`: 0.05
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.16`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline logic yielded a negative Sharpe of `-0.16`.
- Pure mean-reversion (catching falling knives) is famously difficult in crypto because trends are sticky.
- **Optuna Tuning Results**: The optimizer improved the Sharpe ratio to **`0.58`** (Return: `26.3%`, Trades: `983`).
- **Tuned Parameters**: `{'ts_period': 5, 'long_thresh': -0.4, 'short_thresh': -0.6, 'sl_pct': 0.03, 'tp_pct': 0.15}`
- **Conclusion**: Mean-reversion was salvaged by making the lookback period extremely short (`ts_period=5`) and the stop loss incredibly tight (`sl_pct=0.03`). It relies on making almost 1,000 rapid "stabs" at the market, letting the winners run (`tp_pct=0.15`) and cutting losers immediately. While the Sharpe is only mediocre (0.58), the edge is mechanically valid.
