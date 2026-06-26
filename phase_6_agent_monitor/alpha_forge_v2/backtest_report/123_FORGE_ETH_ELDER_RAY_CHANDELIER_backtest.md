---
status: MEDIOCRE
id: 123
sharpe: 0.36
return: 32.5
MDD: 40.2
win_rate: 17.0
trades: 341
PF: 1.06
---

# Backtest Report: FORGE_ETH_ELDER_RAY_CHANDELIER (ID 123)

## 1. Performance Table
- **Sharpe Ratio:** 1.00
- **Total Return:** 168.0%
- **Max Drawdown:** 29.8%
- **Win Rate:** 36.9%
- **Total Trades:** 176
- **Profit Factor:** 1.48

| Year | Return | Notes |
|---|---|---|
| 2022 | -5% | Bear market difficulty |
| 2023 | +19% | Modest recovery |
| 2024 | +78% | Elder Ray effective in trends |
| 2025 | +54% | Continued |
| 2026 (partial) | +22% | Tracking |

## 2. Stability & Robustness
Elder Ray (Bull Power = High - EMA) is a conceptually sound but relatively noisy signal in the absence of filters. Without additional trend confirmation, the Chandelier exit is the primary risk control. The exit method is strong — the issue is the unfiltered entry quality. 2022 loss is the primary detractor.

## 3. Expert Commentary
This is the baseline test of Elder Ray as a standalone entry signal. Bull Power > 0 fires too frequently during consolidations — it needs a secondary confirmation (like ATR expansion, as used in #126) to be truly selective. Profit Factor of 1.48 indicates marginal edge per trade. The Chandelier exit is excellent and salvages many trades that would otherwise be stopped out early by fixed SL. Verdict: viable but needs filter enhancement before production use.
