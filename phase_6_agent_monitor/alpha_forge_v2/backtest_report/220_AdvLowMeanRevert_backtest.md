# Backtest Report: 220_AdvLowMeanRevert

## 1. Strategy Identity
- **ID:** `220`
- **Class:** `AdvLowMeanRevert`
- **Type:** Mean Reversion
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #28: `correlation(adv20, low, 5) + ((high + low) / 2) - close`
- This strategy looks for a specific structural divergence where the rolling average volume (`adv20`) is positively correlated with the `Low` price, meaning sell-offs are drying up on volume. 
- It then calculates the intraday displacement: the difference between the median price of the bar and the actual close. 
- A high value means the close was weak relative to the median, but the volume structure suggests downside exhaustion—triggering a contrarian long.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.41`.
- **Optuna Tuning Results**: The optimizer improved the strategy to a **`0.24`** Sharpe ratio (Return: `6.2%`, Trades: `614`), classifying it as "BAD".
- **Tuned Parameters**: `{'adv_p': 40, 'corr_p': 5, 'long_thresh': 0.1, 'short_thresh': -0.1, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer lengthened the average volume window to 40 periods and tightened the signal thresholds to `0.1` and `-0.1`. However, calculating divergence off the raw dollar gap between median price and close proves to be extremely noisy and fails to extract any meaningful edge in the crypto markets. This strategy will be permanently shelved.
