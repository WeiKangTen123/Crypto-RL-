# Strategy 215: Volume Covariance Fade Backtest Report

## 1. Strategy Overview
- **Name**: Volume Covariance Fade
- **Logic**: Sourced from WorldQuant Alpha #13.
  - Formula: `-rank(covariance(rank(close), rank(volume), 5))`
  - **Entry:** Assumes that high positive covariance between price and volume indicates climax/exhaustion, and generates a negative (short) alpha. 
- **Assets**: `BTC, ETH, BNB, SOL, XRP`
- **Timeframe**: `4h`
- **Date Range**: `2023-05-31` to `2026-05-31`

## 2. Default Parameters
- `cov_p`: 5
- `rank_p`: 10
- `long_thresh`: -0.2
- `short_thresh`: -0.8
- `sl_pct`: 0.08
- `tp_pct`: 0.10

## 3. Initial Baseline Results (Untuned)
- **Sharpe Ratio**: `-1.73`
- **Verdict**: **BAD** (< 0.3) 

## 4. Analysis and Next Steps
- Baseline Sharpe is `-1.73`. This is extremely negative, suggesting that trading against highly covarying price/volume ranks on a short 5-period window is a fast way to get run over by momentum in crypto.
- **Optuna Tuning Results**: The optimizer made a remarkable recovery, pulling the strategy from `-1.73` to a **`0.83`** Sharpe ratio (Return: `46.3%`, Trades: `1380`), placing it in the "MEDIOCRE" category.
- **Tuned Parameters**: `{'cov_p': 10, 'rank_p': 5, 'long_thresh': -0.6, 'short_thresh': -0.4, 'sl_pct': 0.03, 'tp_pct': 0.1}`
- **Conclusion**: The optimizer doubled the covariance lookback (`cov_p=10`) while halving the rank normalization window (`rank_p=5`). This effectively measures longer-term covariance between highly volatile, short-term rank shifts. It generates a massive number of trades (1380) and relies entirely on extremely tight stops (`sl_pct=0.03`). While technically profitable, it acts more like a high-frequency noise-harvester than a strong directional indicator.
