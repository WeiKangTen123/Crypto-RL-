# Strategy 207: VWAP Distance x Volume Delta Backtest Report

## 1. Strategy Overview
- **Name**: VWAP Distance x Volume Delta
- **Logic**: Sourced from WorldQuant Alpha #5.
  - Formula: `rank(open - SMA(vwap, 10)) * sign(close - vwap) * rank(abs(close - vwap))`
  - **Entry:** Produces an alpha bound between -1 and 1. A high positive score indicates the asset opened far above its historical VWAP, closed above its current VWAP, and closed very far away from the VWAP (high momentum breakout). Enters Long on high positive, Short on high negative.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ts_p`: 10
- `long_thresh`: 0.6
- `short_thresh`: -0.6
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-1.17`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline result yielded a severe negative Sharpe of `-1.17`.
- The compound nature of the 3-term multiplication causes high volatility in the signal.
- **Optuna Tuning Results**: The optimizer struggled to find a robust edge, peaking at a Sharpe of **`0.27`** (Return: `10.1%`, Trades: `463`).
- **Tuned Parameters**: `{'ts_p': 20, 'long_thresh': 0.8, 'short_thresh': -0.8, 'sl_pct': 0.03, 'tp_pct': 0.15}`
- **Conclusion**: Even after extending the VWAP window (`ts_p=20`) and demanding extreme signal conviction (`long_thresh=0.8`), the strategy failed to cross the `0.30` viable threshold. The volatility of crypto volume combined with VWAP distance creates too many false breakout signals. This factor remains in the **BAD** tier and will not be deployed without further structural modifications.
