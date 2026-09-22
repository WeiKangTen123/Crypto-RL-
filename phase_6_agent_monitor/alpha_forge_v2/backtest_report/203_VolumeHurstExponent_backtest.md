# Strategy 203: Volume Hurst Exponent Backtest Report

## 1. Strategy Overview
- **Name**: Volume Hurst Exponent
- **Logic**: Sourced from the "Multifractal Post-COVID" research paper. Calculates the Hurst exponent `h(2)` on trading volume using a vectorized rolling Variance Ratio approximation.
  - If `H > 0.5`: Volume is persistent (volume surges are followed by more volume surges).
  - **Entry:** Acts as a momentum filter. When volume is persistent (`H > threshold`) and price is breaking out (`Close > SMA`), we enter a Long position.
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `hurst_period`: 100
- `hurst_thresh`: 0.55
- `sma_period`: 20
- `sl_pct`: 0.08
- `tp_pct`: 0.15

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-0.87`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline logic yielded a strongly negative Sharpe of `-0.87`.
- Volume persistence is notoriously difficult to capture cleanly with a single fixed threshold (like `0.55`), because different coins exhibit different baseline fractal dimensions.
- **Optuna Tuning Results**: The optimizer was able to recover this strategy from `-0.87` up to a **`0.6`** Sharpe (Return: `10.9%`, Trades: `122`), bringing it securely into the "MEDIOCRE" (viable) category.
- **Tuned Parameters**: `{'hurst_period': 60, 'hurst_thresh': 0.52, 'sma_period': 20, 'sl_pct': 0.05, 'tp_pct': 0.05}`
- **Conclusion**: The optimizer significantly shortened the lookback window to `60` and lowered the persistence threshold to `0.52`. This suggests that in crypto, volume regimes are highly transient. By acting on shorter, milder signals of volume persistence (just slightly above the 0.50 random walk threshold), the strategy is able to catch bursts of momentum much faster.
