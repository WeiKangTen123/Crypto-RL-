# Backtest Report: 218_StddevGapCross

## 1. Strategy Identity
- **ID:** `218`
- **Class:** `StddevGapCross`
- **Type:** Volatility Regime / Trend
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #18: `-rank(ts_rank(stddev(abs(close - open), 5), 5) + ts_rank(stddev(close, 5), 5))`
- This strategy measures two distinct forms of volatility: the standard deviation of the true candle body `abs(close - open)`, and the standard deviation of the closing prices.
- It aggregates the time-series ranks of both measurements. High values indicate an explosion in intra-candle and inter-candle volatility. The `-1` multiplier attempts to fade these volatility spikes.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `0.15`. 
- **Optuna Tuning Results**: The optimizer improved the baseline slightly to a **`0.51`** Sharpe ratio (Return: `43.7%`, Trades: `332`), which classifies it as "MEDIOCRE".
- **Tuned Parameters**: `{'std_p': 3, 'ts_p': 5, 'rank_p': 5, 'long_thresh': -0.6, 'short_thresh': -1.6, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer shortened the standard deviation lookback to 3 periods and the rank lookback to 5, increasing the strategy's sensitivity to extremely short-term volatility bursts. It uses an asymmetric entry profile (`-0.6` long vs `-1.6` short) to account for crypto's natural upward bias, but overall struggles to find a highly robust edge.
