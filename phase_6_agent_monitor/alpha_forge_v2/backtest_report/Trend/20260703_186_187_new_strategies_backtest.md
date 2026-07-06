# Backtest Report — New Strategies (2026-07-03, batch 2)
**Strategies:** 186, 187 | **Period:** 2021-01-01 → 2026-05-31 | **Leverage:** 10× | **150 finetune trials each**

---

## Results Summary

| ID | Strategy | Class | Coin | TF | Return | Sharpe | MDD | WR | Trades | Grade |
|---|---|---|---|---|---|---|---|---|---|---|
| 186 | Fisher Extreme Reversal | FisherExtremeReversalStrategy | BTC | 1H | +1.26% | 0.07 | 7.0% | 29.4% | 34 | BAD |
| 187 | Tight Bollinger Scalper | TightBollingerScalperStrategy | BTC | 1H | -99.98% | -5.65 | 99.9% | 47.4% | 3124 | BAD |

---

## Analysis

### ID 186 — Fisher Extreme Reversal (BAD)
Extreme threshold (Fisher > 1.84) makes signals very rare — only 34 trades in 5.5yr. The edge concept is sound but signal frequency is too low for reliable statistics. Best Sharpe achievable was 0.07.
**Diagnosis:** BTC's trend regime means Fisher rarely hits extreme reversals. Might work better on ETH or SOL which have more intraday volatility.

### ID 187 — Tight Bollinger Scalper (BAD — structural)
Over-trading confirmed structural failure: 3124 trades on BTC 1H means ~1.5 trades/day. The "close-back-inside" logic triggers nearly every BB touch. Fees destroy all P&L (PF 0.66). Even after finetune, best Sharpe is -5.65.
**Diagnosis:** BTC 1H is too trending for tight BB mean-reversion. Strategy requires genuinely ranging markets (stablecoin pairs, low-vol assets).

---

## Factor Cards Updated
- `factor_library/Mean_Reversion/20260527_fisher_transform_reversal.md` → COMPLETED (built, backtested, finetuned, BAD)
- `factor_library/Mean_Reversion/20260526_tight_bollinger_scalper.md` → COMPLETED (built, backtested, finetuned, BAD)

## Stale Cards Also Resolved (17 total)
All previously QUEUED cards with existing registered strategies were marked COMPLETED.
Rejected cards (Keltner RSI x2, Envelope, Triple Confirm FVMA) marked COMPLETED + REJECTED.

---
*Dev Reports:*
- `dev_report/Trend/20260703_186_FisherExtremeReversalStrategy_dev.md`
- `dev_report/Trend/20260703_187_TightBollingerScalperStrategy_dev.md`
