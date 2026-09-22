# Backtest Report: 225_OhlcGapRatio

## 1. Strategy Identity
- **ID:** `225`
- **Class:** `OhlcGapRatio`
- **Type:** Structural Momentum
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)

## 2. Core Logic
- Implements WorldQuant Alpha #101: `(close - open) / (high - low + 0.001)`
- Calculates what percentage of the entire candle's high-low range is made up of the actual body (close-open). 
- Values near `1.0` indicate the coin closed on its absolute high (maximum bullishness), while values near `-1.0` indicate it closed on its absolute low (maximum bearishness).

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe across the 10-coin portfolio is `-1.10`.
- **Optuna Tuning Results (Round 2)**: Expanding the optimization ranges did not unlock a hidden edge. The optimizer merely found a slightly different local maximum, returning a **`0.27`** Sharpe ratio (Return: `11.4%`, Trades: `174`), keeping it trapped in the "BAD/MEDIOCRE" bucket.
- **Tuned Parameters**: `{'long_thresh': 0.95, 'short_thresh': -0.9, 'sl_pct': 0.05, 'tp_pct': 0.2}`
- **Conclusion**: Even when allowed to search wildly different parameter bounds, Alpha 101's logic simply doesn't map well to crypto. By requiring a `0.95` entry threshold, it demands near mathematical perfection from a candle's structure, starving the strategy of trades (only 174 over 3 years across 10 coins). It lacks a robust statistical edge and will be shelved.
