# Backtest Report: 222_VolCloseAntiMom

## 1. Strategy Identity
- **ID:** `222`
- **Class:** `VolCloseAntiMom`
- **Type:** Momentum Divergence
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #12: `sign(delta(volume, 1)) * (-1 * delta(close, 1))`
- The alpha captures situations where trading volume is expanding (positive sign) while the price is dropping, which is often a signal of panic selling/exhaustion. 
- The strategy will attempt to buy the dip when volume surges downward, and sell when volume surges upward.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `-0.29`.
- **Optuna Tuning Results**: The optimizer improved the strategy out of the negative range, securing a **`0.30`** Sharpe ratio (Return: `9.7%`, Trades: `340`), which categorizes it as "MEDIOCRE".
- **Tuned Parameters**: `{'delta_p': 1, 'long_thresh': 5.0, 'short_thresh': -20.0, 'sl_pct': 0.08, 'tp_pct': 0.15}`
- **Conclusion**: The optimizer significantly lowered the long threshold to `5.0` to catch smaller volume surges while maintaining a strict short threshold of `-20.0`. However, the mathematical purity of Alpha #12 struggles heavily against crypto's erratic volume spikes, failing to produce a robust edge. This strategy will be shelved.
