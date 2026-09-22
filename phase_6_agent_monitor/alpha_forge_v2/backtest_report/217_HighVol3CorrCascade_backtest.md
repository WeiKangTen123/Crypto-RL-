# Backtest Report: 217_HighVol3CorrCascade

## 1. Strategy Identity
- **ID:** `217`
- **Class:** `HighVol3CorrCascade`
- **Type:** Contrarian / Mean Reversion
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #15: `-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3)`
- This strategy calculates the rolling correlation between the rank of High prices and the rank of Volumes, taking a short-term 3-period window.
- It then computes the rank of this correlation, and takes a rolling 3-period sum.
- A high positive correlation between price peaks and volume peaks often indicates FOMO blow-off tops, hence the contrarian `-1` multiplier. 

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.10`.
- **Optuna Tuning Results**: The optimizer improved the strategy slightly to a **`0.45`** Sharpe ratio (Return: `13.4%`, Trades: `399`), classifying it as "MEDIOCRE".
- **Tuned Parameters**: `{'corr_p': 10, 'sum_p': 5, 'rank_p': 5, 'long_thresh': -1.5, 'short_thresh': -1.5, 'sl_pct': 0.08, 'tp_pct': 0.1}`
- **Conclusion**: The optimizer significantly extended the correlation lookback window to 10 periods but tightened the rank and sum windows to 5. It seems this alpha struggles to extract significant excess return despite optimization, heavily relying on the short side threshold matching the long side threshold (`-1.5`) which suggests it's primarily fading extreme macro structures without strong directional bias.
