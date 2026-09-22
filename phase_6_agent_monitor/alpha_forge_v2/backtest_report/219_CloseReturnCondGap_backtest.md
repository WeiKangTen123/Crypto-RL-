# Backtest Report: 219_CloseReturnCondGap

## 1. Strategy Identity
- **ID:** `219`
- **Class:** `CloseReturnCondGap`
- **Type:** Momentum Divergence
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #19 (simplified): `-sign(delta(close, 7)) * (1 + rank(sum(returns, 250)))`
- The alpha multiplies the inverse sign of the short-term price momentum (`delta(close, 7)`) by the rank of the long-term accumulated return (`sum(returns, 60)`).
- This creates a powerful mean-reverting dynamic where short-term pullbacks in a strong macro uptrend are heavily bought, and short-term pumps in a macro downtrend are faded.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.63`.
- **Optuna Tuning Results**: The optimizer improved the strategy from its negative baseline, reaching a **`0.26`** Sharpe ratio (Return: `7.8%`, Trades: `397`), classifying it as "BAD".
- **Tuned Parameters**: `{'delta_p': 7, 'sum_p': 20, 'rank_p': 10, 'long_thresh': 0.8, 'short_thresh': -0.8, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer significantly shortened the macro return aggregator (`sum_p=20`) to try to respond faster to short-term regime shifts, but the conditional gap logic simply doesn't hold enough predictive power to overcome crypto's high-noise environment. At `0.26` Sharpe, the strategy lacks a meaningful edge and will be shelved.
