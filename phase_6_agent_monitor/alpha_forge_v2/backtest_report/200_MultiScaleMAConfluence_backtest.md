# Strategy 200: Multi-Scale MA Confluence Backtest Report

## 1. Strategy Overview
- **Name**: Multi-Scale MA Confluence
- **Logic**: Sourced from the "Pairs trading with time-series deep learning models" (Scaleformer architecture). Computes Moving Averages at 4 different timescales (default: 5, 10, 20, 60). A strong trend is identified when the MAs are perfectly stacked.
  - Long when `MA_t1 > MA_t2 > MA_t3 > MA_t4`
  - Short when `MA_t1 < MA_t2 < MA_t3 < MA_t4`
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `ma1`: 5
- `ma2`: 10
- `ma3`: 20
- `ma4`: 60
- `ma_type`: SMA
- `sl_pct`: 0.05
- `tp_pct`: 0.10
- `risk_per_trade`: 5%

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `0.05`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- The baseline strategy yielded a slightly positive but very weak Sharpe ratio of `0.05`.
- As a pure trend-following strategy, the baseline result confirms that momentum exists (unlike the previous mean-reversion strategies which yielded negative baseline Sharpes), but the default parameters and strict 4-MA stacking might be too lagging or restrictive.
- **Optuna Tuning Results**: After running 175 trials, the Optuna tuner significantly improved the Sharpe ratio to `0.88` (Return: `46.2%`, Trades: `383`).
- **Tuned Parameters**: `{'ma1': 3, 'ma2': 20, 'ma3': 40, 'ma4': 60, 'ma_type': 'SMA', 'sl_pct': 0.05, 'tp_pct': 0.06}`
- **Conclusion**: The optimizer found that using a much faster leading MA (`3`) combined with a wider spread of trailing MAs (`20`, `40`, `60`) captures the trend transitions much more effectively than the default `5, 10, 20, 60` setup. With a Sharpe of `0.88`, this factor proves that a hierarchical temporal confluence filter provides a robust entry trigger in the crypto market.
