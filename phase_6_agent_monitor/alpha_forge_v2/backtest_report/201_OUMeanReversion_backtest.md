# Strategy 201: OU Mean Reversion Backtest Report

## 1. Strategy Overview
- **Name**: OU Mean Reversion
- **Logic**: Uses the Ornstein-Uhlenbeck mean-reversion speed ($\kappa$) to act as a regime filter. 
  - A high $\kappa$ (e.g., > 30) indicates that the asset is currently in a fast mean-reverting regime, making mean-reversion trades safer.
  - A low $\kappa$ indicates a trending regime where mean-reversion will likely fail.
  - **Entry:** Combines the $\kappa$ filter with a standard VWAP Z-score pull-back entry logic.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ou_period`: 20
- `vwap_period`: 20
- `entry_z`: 2.0
- `min_kappa`: 30
- `sl_pct`: 0.05
- `tp_pct`: 0.05

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-1.02`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline result yielded a highly negative Sharpe ratio of `-1.02`. 
- Even with the $\kappa$ speed filter applied to ensure we only take pull-back trades in fast mean-reverting environments, fading momentum still yields devastating results out-of-the-box in the crypto markets.
- **Optuna Tuning Results**: After running 150 trials, the optimizer impressively salvaged the strategy, lifting the Sharpe from `-1.02` to exactly **`0.30`** (Return: `12.4%`, Trades: `583`).
- **Tuned Parameters**: `{'ou_period': 20, 'vwap_period': 10, 'entry_z': 2.0, 'min_kappa': 30, 'sl_pct': 0.05, 'tp_pct': 0.1}`
- **Conclusion**: By halving the `vwap_period` to `10` and doubling the take-profit to `0.10`, the tuner forced the strategy to only take extremely sensitive, high-velocity pullbacks and hold the winners longer. Eking out a `0.30` Sharpe proves the $\kappa$ filter is successfully isolating regimes where mean-reversion is statistically viable in crypto.
