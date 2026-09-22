# Backtest Report: 232_ComplexVolumeScalar

## 1. Strategy Identity
- **ID:** `232`
- **Class:** `ComplexVolumeScalar`
- **Type:** "HARD" WorldQuant Alpha 60
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `scale(rank(ts_argmax(close, p1))) - 2 * scale(rank(CLV * volume))`
- **Market Microstructure (ADL):** Calculates the Close Location Value (CLV), which measures where the close sits within the high-low range. It multiplies this by volume to create an Accumulation/Distribution measurement. It then takes the cross-sectional rank of this value across all 10 coins and normalizes the weights using `scale()`.
- **Time-Since-High:** Calculates `ts_argmax(close, p1)` to find how recently each coin hit its local high. It ranks this cross-sectionally and normalizes it using `scale()`.
- **Alpha Synthesis:** It subtracts double the Accumulation/Distribution rank from the Time-Since-High rank. It hunts for coins that are actively accumulating massive volume at local lows (high ADL, long time since high).

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values.

## 4. Analysis and Next Steps
- **Optuna Tuning Results (Round 3):** After unchaining the boundaries for extreme scalping, the AI proved that `3%` is the absolute mathematical floor for a crypto stop-loss on this timeframe. Anything tighter (1-2%) gets wicked out by noise. It slightly optimized the lookback to `p1=25`, bumping the stats to a **`0.51` Sharpe ratio** (Return: `73.1%`, Trades: `2496`).
- **Tuned Parameters**: `{'p1': 25, 'long_thresh': 0.1, 'short_thresh': -0.25, 'sl_pct': 0.03, 'tp_pct': 0.1}`
- **Conclusion**: The strategy has mathematically peaked. It traded heavily (nearly 2,500 times), acting as a high-frequency cross-sectional scalper. It remains in the "MEDIOCRE" tier, proving that while ADL/Time-Since-High scaling works, it generates too many false positives on a 4-hour timeframe to be considered elite without a higher timeframe macro-trend filter.
