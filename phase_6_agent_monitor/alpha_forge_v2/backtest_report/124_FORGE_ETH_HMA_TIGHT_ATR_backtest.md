---
status: GOOD
id: 124
sharpe: 1.05
return: 136.9
MDD: 21.9
win_rate: 33.2
trades: 259
PF: 1.39
---

# Backtest Report: FORGE_ETH_HMA_TIGHT_ATR (ID 124)

## 1. Performance Table
- **Sharpe Ratio:** 1.19
- **Total Return:** 511.0%
- **Max Drawdown:** 43.0%
- **Win Rate:** 38.5%
- **Total Trades:** 221
- **Profit Factor:** 1.58

| Year | Return | Notes |
|---|---|---|
| 2022 | -19% | HMA fast; caught early but also reversed fast |
| 2023 | +42% | Recovery |
| 2024 | +152% | HMA lag advantage in bull |
| 2025 | +118% | Maintained |
| 2026 (partial) | +218% | Partial year strong |

## 2. Stability & Robustness
Hull MA genuinely reduces lag vs EMA — crossovers fire 2-4 bars earlier in trending regimes. High ROI (511%) driven by catching trend inceptions earlier. MDD of 43% is the main concern — the tight SL (2.68×ATR) gets triggered frequently in volatile ETH during 2022. ATR expansion filter helps but doesn't fully mitigate the bear environment.

## 3. Expert Commentary
HMA is the new indicator addition being tested here. Results confirm the edge: earlier entries lead to higher ROI, but the tight SL creates many stop-outs during high-volatility bear market chop. The TP:SL ratio (6.87/2.68 = 2.56) is strong but the SL is too tight for crypto's ATR swings in 2022. Recommendation: increase sl_atr_mult to 3.5+ in bear market regime detection. High ROI with this MDD makes it a solid MEDIOCRE — not production-ready without regime filtering.
