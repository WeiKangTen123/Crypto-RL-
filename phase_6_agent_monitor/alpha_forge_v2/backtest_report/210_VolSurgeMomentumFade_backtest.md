# Strategy 210: Volume Surge Momentum Fade Backtest Report

## 1. Strategy Overview
- **Name**: Volume Surge Momentum Fade
- **Logic**: Sourced from WorldQuant Alpha #7.
  - Formula: `(adv20 < vol) ? -ts_rank(abs(delta(close, 7)), 60) * sign(delta(close, 7)) : -1`
  - **Entry:** When current volume exceeds the 20-period moving average, it triggers the conditional logic. If the price moved up over the last 7 periods, the alpha is negative. If it moved down, the alpha is positive. The magnitude is determined by the 60-period time-series rank of the absolute price change.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `sma_p`: 20
- `delta_p`: 7
- `ts_p`: 60
- `long_thresh`: 0.6
- `short_thresh`: -0.6
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.18`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The raw baseline gives a negative Sharpe `-0.18`.
- **Optuna Tuning Results**: The optimizer improved the edge, reaching a Sharpe ratio of **`0.68`** (Return: `34.6%`, Trades: `790`), placing it in the "MEDIOCRE" category.
- **Tuned Parameters**: `{'sma_p': 30, 'delta_p': 10, 'ts_p': 60, 'long_thresh': 0.5, 'short_thresh': -0.5, 'sl_pct': 0.03, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer extracted an edge by expanding the volume baseline to a 30-period average (`sma_p=30`) and the momentum lookback to 10 periods (`delta_p=10`). When volume surges past the 30-period average, fading the 10-period momentum produces a slightly profitable, high-frequency edge (790 trades), relying heavily on tight stops (`sl_pct=0.03`) and wide take-profits (`tp_pct=0.15`). While mechanically valid, its predictive power isn't as robust as the divergence factors.
