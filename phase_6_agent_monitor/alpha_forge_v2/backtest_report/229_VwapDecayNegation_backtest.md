# Backtest Report: 229_VwapDecayNegation

## 1. Strategy Identity
- **ID:** `229`
- **Class:** `VwapDecayNegation`
- **Type:** "HARD" WorldQuant Alpha 57
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `-(1 * ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2)))`
- **VWAP Negation:** The strategy measures the simple mean-reversion strength of price drifting away from its VWAP (calculated via Typical Price). Since it negates this value, it looks to buy when the price drops *below* VWAP.
- **Decay Time-Scaling:** The true magic of Alpha 57 is the denominator. It finds the cross-sectional rank of how long it has been since each coin hit its 30-bar high (`ts_argmax`), and passes that through a `decay_linear` filter.
- **Action:** By dividing the VWAP distance by this decayed rank, it scales the strength of the mean-reversion signal. Coins that dropped from a recent high but are now massively under VWAP will show anomalous readings, triggering entries.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values.

## 4. Analysis and Next Steps
- **Baseline:** The raw unoptimized baseline produced a brutal `-1.31` Sharpe.
- **Optuna Tuning Results (Round 2):** Expanding the optimizer bounds even further yielded almost no improvement. It peaked at a **`0.31` Sharpe ratio** (Return: `24.8%`, Trades: `504`), proving this structural logic is inherently flawed for Crypto.
- **Tuned Parameters**: `{'p1': 300, 'p2': 10, 'long_thresh': 0.6, 'short_thresh': 0.6, 'sl_pct': 0.15, 'tp_pct': 0.5}`
- **Conclusion**: The AI tried to save the strategy by stretching the `ts_argmax` window all the way out to a massive `300` bars (50 days), but it barely moved the needle. Scaling a VWAP deviation by the cross-sectional rank of "time since highest high" just doesn't provide a reliable statistical edge in crypto. In equities, this might work for identifying over-sold laggards, but in crypto's highly correlated macro-regimes, this type of mean-reversion is far too weak to survive 5 years of structural shifts. This strategy is officially classified as a failure.
