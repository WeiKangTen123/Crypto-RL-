# Strategy 208: Volatility Regime Reversal Backtest Report

## 1. Strategy Overview
- **Name**: Volatility Regime Reversal
- **Logic**: Sourced from WorldQuant Alpha #1.
  - Formula: `rank(argmax(sign(ret<0) ? std(ret,20) : close, 5)) - 0.5`
  - **Entry:** Computes an array where down-bars are represented by their trailing standard deviation and up-bars by their closing price. Finds the rolling argmax, and ranks it. We enter trades based on extreme values of this regime-adjusted volatility rank.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `std_p`: 20
- `argmax_p`: 5
- `ts_p`: 10
- `long_thresh`: 0.3
- `short_thresh`: -0.3
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.08`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline result yielded a slight negative Sharpe of `-0.08`, meaning it trades basically at random.
- The default thresholds (`0.3` and `-0.3`) are quite wide since the alpha ranges between `-0.5` and `0.5`.
- **Optuna Tuning Results**: The optimizer improved the edge, reaching a Sharpe ratio of **`0.48`** (Return: `38.2%`, Trades: `461`), pushing it into the "MEDIOCRE" category.
- **Tuned Parameters**: `{'std_p': 30, 'argmax_p': 3, 'ts_p': 20, 'long_thresh': 0.3, 'short_thresh': -0.4, 'sl_pct': 0.05, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer extracted edge by expanding the trailing std dev window (`std_p=30`) and the time-series rank window (`ts_p=20`), while making the argmax window very tight (`argmax_p=3`). This identifies highly specific short-term regime peaks against a longer-term backdrop. While tradable, the Sharpe ratio is unremarkable (0.48), confirming that complex nested conditional factors often struggle to generalize in crypto without extensive overfitting.
