# Backtest Report: 223_OpenCloseRatioRank

## 1. Strategy Identity
- **ID:** `223`
- **Class:** `OpenCloseRatioRank`
- **Type:** Mean Reversion
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #33: `rank(-1 * ((1 - (open / close))))`
- This algorithm computes the ratio of the open price against the close price. If `open/close` is very low, it means the close is significantly higher than the open (a massive green candle).
- The formula inverts this relationship and calculates a time-series rank. It essentially looks for extreme momentum candles and attempts to fade them (mean reversion) by buying extreme red candles and shorting extreme green candles relative to recent history.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `-1.60`.
- **Optuna Tuning Results**: The optimizer made an impressive recovery from a deeply negative baseline, pulling the strategy up to a **`0.48`** Sharpe ratio (Return: `37.5%`, Trades: `633`), classifying it as "MEDIOCRE".
- **Tuned Parameters**: `{'rank_p': 5, 'long_thresh': 0.6, 'short_thresh': 0.05, 'sl_pct': 0.03, 'tp_pct': 0.15}`
- **Conclusion**: Optuna tightened the rolling rank period to 5 and significantly lowered the entry thresholds (`0.6` for long and `0.05` for short) to ensure trades only fire on the most extreme relative candle structures. While it generated a decent 37.5% return, it couldn't reliably secure a >1.0 Sharpe edge and will remain in the Mediocre bucket.
