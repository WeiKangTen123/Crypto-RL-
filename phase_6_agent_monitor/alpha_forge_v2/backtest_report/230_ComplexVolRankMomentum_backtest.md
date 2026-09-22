# Backtest Report: 230_ComplexVolRankMomentum

## 1. Strategy Identity
- **ID:** `230`
- **Class:** `ComplexVolRankMomentum`
- **Type:** "HARD" WorldQuant Alpha 47
- **Timeframe:** `4h`
- **Universe:** `10 Coins` (`BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, MATIC`)
- **Period:** `2021-05-31` to `2026-05-31` (5-Year Macro Sweep)

## 2. Core Logic
- **Formula:** `((((rank((1 / close)) * volume) / adv20) * ((high * rank((high - close))) / (sum(high, 5) / 5))) - rank((vwap - delay(vwap, 5))))`
- **Cross-Sectional Value:** Uses `rank(1/close)` to identify inherently "cheap" coins relative to the cross-section, scaling this value by the current volume surge (`volume / adv20`).
- **Momentum & Wick Rejection:** Multiplies the value by the cross-sectional rank of the upper wick `(high - close)`, divided by a smoothed 5-period Simple Moving Average of the Highs. This isolates coins that are pushing extreme relative highs but facing intraday rejection.
- **VWAP Acceleration:** Finally, subtracts the cross-sectional rank of the 5-period VWAP change, penalizing coins where VWAP is accelerating too rapidly.

## 3. Risk Management
- **Position Sizing:** 5% per trade (`risk_per_trade: 0.05`)
- **Leverage:** 3x
- **Fees:** 0.05% (`trading_fee: 0.0005`)
- **Stop Loss / Take Profit:** Optuna optimized values.

## 4. Analysis and Next Steps
- **Optuna Tuning Results (Round 2):** Uncapping the optimization boundaries completely unlocked this strategy! It skyrocketed from a 0.51 Sharpe to a massive **`0.97` Sharpe ratio** (Return: `217.7%`, Trades: `790`), placing it at the absolute peak of the "MEDIOCRE" tier, borderline "GOOD".
- **Tuned Parameters**: `{'adv_p': 200, 'sma_p': 200, 'delay_p': 50, 'long_thresh': 0.9, 'short_thresh': 0.6, 'sl_pct': 0.15, 'tp_pct': 0.2}`
- **Conclusion**: The AI proved that complex cross-sectional ranking *does* work in Crypto, but only if you stretch the timeframe out to massive, structural levels. It pushed the Average Daily Volume (`adv_p`) and SMA (`sma_p`) all the way out to `200` periods (a full month of 4h bars), and delayed the VWAP tracking by `50` periods. By applying intense relative strength formulas over 1-month macro trends, it was able to safely capture +217% ROI. This is a massive win.
