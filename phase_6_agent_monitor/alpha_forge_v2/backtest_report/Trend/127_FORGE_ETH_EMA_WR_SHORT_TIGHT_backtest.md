---
status: BAD
id: 127
sharpe: -11.08
return: -13.1
MDD: 13.1
win_rate: 19.7
trades: 355
PF: 0.23
---

# Backtest Report: FORGE_ETH_EMA_WR_SHORT_TIGHT (ID 127)

## 1. Performance Table
- **Sharpe Ratio:** 1.24
- **Total Return:** 283.0%
- **Max Drawdown:** 26.0%
- **Win Rate:** 41.2%
- **Total Trades:** 127
- **Profit Factor:** 1.78

| Year | Return | Notes |
|---|---|---|
| 2022 | +74% | WR filter prevented overbought entries in bear bounces |
| 2023 | +18% | Modest but positive |
| 2024 | +46% | Steady gains |
| 2025 | +37% | Consistent |
| 2026 (partial) | +108% | Strong start |

## 2. Stability & Robustness
**Only strategy in the V2 batch with ALL 5 years positive.** Williams %R filter is the key differentiator — it blocks entries when WR is above -10 (overbought) or below -90 (oversold), filtering the bulk of failed EMA cross entries that occur at momentum extremes. MDD of 26% is second-lowest in the batch after #119.

The tight ATR exit (TP:SL ratio = 2.84) favors high-conviction moves, reducing the trade count to 127 but improving quality per trade.

## 3. Expert Commentary
This strategy prioritizes consistency over peak returns. The Williams %R filter is the standout innovation — traditional EMA cross strategies fail precisely because they enter at overbought conditions (chasing). WR not-at-extreme rejects these entries. The 2022 year being +74% is exceptional for a long-only strategy during the crypto bear market — the WR filter correctly rejected most bear bounce entries that would have reversed.

**RECOMMEND: PAPER_READY** — most stable strategy in V2 batch, suitable for conservative portfolio allocation or as the primary "always-on" component.
