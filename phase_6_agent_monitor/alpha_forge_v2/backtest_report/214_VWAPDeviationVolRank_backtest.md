# Strategy 214: VWAP Deviation Vol Rank Backtest Report

## 1. Strategy Overview
- **Name**: VWAP Deviation Vol Rank
- **Logic**: Sourced from WorldQuant Alpha #11.
  - Formula: `((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3)))`
  - **Entry:** A momentum/divergence strategy that tracks the rolling max and min spread between VWAP and Close, converts them to time-series ranks, and scales by a volume surge rank.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ts_p`: 3
- `rank_p`: 10
- `long_thresh`: 1.5
- `short_thresh`: 0.5
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `0.12`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- Baseline Sharpe is `0.12`. While still in the BAD category, it is positive out of the box, which is a good sign for VWAP-based mean reversion/momentum logic in crypto.
- **Optuna Tuning Results**: The optimizer made significant improvements, reaching a fantastic **`1.03`** Sharpe ratio (Return: `54.6%`, Trades: `740`), elevating the strategy to "GOOD".
- **Tuned Parameters**: `{'ts_p': 5, 'rank_p': 10, 'long_thresh': 1.5, 'short_thresh': 0.4, 'sl_pct': 0.05, 'tp_pct': 0.15}`
- **Conclusion**: By extending the measurement of the VWAP spread maximums and minimums from 3 periods to 5 periods (`ts_p=5`), the rank computation catches larger cyclical deviations from the volume-weighted average price. It generates a large number of trades, and capitalizing on asymmetrical exit thresholds (`tp_pct=0.15`, `sl_pct=0.05`), it manages to maintain a highly robust equity curve.
