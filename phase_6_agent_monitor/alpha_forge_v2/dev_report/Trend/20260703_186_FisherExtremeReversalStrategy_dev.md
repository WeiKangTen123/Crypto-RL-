---
id: 186
strategy: FisherExtremeReversalStrategy
date: 2026-07-03
grade: BAD
status: FINETUNED
---
# Dev Report: FisherExtremeReversalStrategy (ID 186)

## Factor Card
`factor_library/Mean_Reversion/20260527_fisher_transform_reversal.md`

## Logic
Fisher Transform extreme reversal: entry only when Fisher spikes past ±threshold AND crosses EMA signal line. TP when Fisher returns to zero. SL at ATR multiple.

| Metric | Baseline | Finetuned |
|---|---|---|
| Sharpe | -1.35 | 0.07 |
| Return | -62.35% | +1.26% |
| MDD | 62.89% | 7.02% |
| WR | 43.17% | 29.41% |
| Trades | 315 | 34 |
| PF | 0.58 | 1.05 |

**Key params:** extreme_thresh 1.5→1.84, signal_period 5→12, sl_atr_mult 1.5→0.50

## Diagnosis
Fisher extreme threshold works as a filter but makes entries too rare (34 trades/5.5yr). The concept is valid — Fisher extremes do predict reversals — but BTC 1H doesn't hit true extremes often enough for statistical significance. Alternative: test on ETH/SOL where intraday volatility is higher.

## Grade: BAD
