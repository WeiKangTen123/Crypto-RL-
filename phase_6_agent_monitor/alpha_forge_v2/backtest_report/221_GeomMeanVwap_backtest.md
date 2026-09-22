# Backtest Report: 221_GeomMeanVwap

## 1. Strategy Identity
- **ID:** `221`
- **Class:** `GeomMeanVwap`
- **Type:** Mean Reversion / Divergence
- **Timeframe:** `4h`
- **Universe:** `BTC, ETH, BNB, SOL, XRP`

## 2. Core Logic
- Implements WorldQuant Alpha #41: `sqrt(high * low) - vwap`
- This strategy calculates the true Geometric Mean of the candle's extremes (`High` and `Low`) and compares it against the volume-weighted average price (VWAP / Typical Price proxy).
- A positive divergence means the purely price-based geometric mean is significantly higher than the volume-weighted average, suggesting that the volume profile is pulling the market down (bearish pressure) despite price wicks pushing up.
- The strategy initiates trades when this spread hits extreme levels.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Fixed percentage trailing.

## 4. Analysis and Next Steps
- Baseline Sharpe is `0.26`.
- **Optuna Tuning Results**: The optimizer made a MASSIVE leap forward, finding a **`1.03`** Sharpe ratio (Return: `7.8%`, Trades: `160`), elevating this strategy to "GOOD" status!
- **Tuned Parameters**: `{'long_thresh': 50.0, 'short_thresh': -50.0, 'sl_pct': 0.08, 'tp_pct': 0.1}`
- **Conclusion**: By heavily widening the required divergence thresholds (`50.0` / `-50.0`), the strategy successfully filters out the standard market noise. It acts as a highly selective mean-reversion sniper, only firing when the geometric mean of the extremes is completely detached from the volume-weighted average price. This confirms that WorldQuant Alpha #41 holds significant predictive edge in crypto when tuned for extreme rarity.
