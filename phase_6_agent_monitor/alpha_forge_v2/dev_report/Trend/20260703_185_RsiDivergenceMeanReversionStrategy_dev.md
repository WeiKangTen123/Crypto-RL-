---
id: 185
strategy: RsiDivergenceMeanReversionStrategy
date: 2026-07-03
grade: BAD
status: BASELINE
---
# Dev Report: RsiDivergenceMeanReversionStrategy (ID 185)

## Factor Card
`factor_library/Mean_Reversion/20260526_rsi_divergence_mean_reversion.md`

## Logic
RSI divergence detection (causal, symmetric pivot window) gated by ADX < 25 (ranging market only).
- **Bullish div**: price lower low + RSI higher low → Long
- **Bearish div**: price higher high + RSI lower high → Short
- **TP**: BB midline (mean reversion complete); **SL**: 1.5× ATR

## Baseline Results (BTC 4H, 2021–2026, no finetune)
| Metric | Value |
|---|---|
| Total Return | -30.65% |
| Sharpe Ratio | -1.25 |
| Max Drawdown | 31.33% |
| Win Rate | 22.58% |
| Total Trades | 31 |
| Profit Factor | 0.12 |

| Year | Return |
|---|---|
| 2021 | -15.11% |
| 2022 | -5.03% |
| 2023 | -0.98% |
| 2024 | -4.39% |
| 2025 | -6.74% |
| 2026 | -2.57% |

## Analysis
Negative across all 6 years. Only 31 trades in 5.5yr with 22.6% win rate — divergence signals on BTC 4H are rare and mostly false at these parameters. PF 0.12 = extremely poor edge. The ADX < 25 gate, while conceptually correct, makes the strategy too rare to generate enough signal.

**Likely issues:** div_lookback=40 bars is aggressive (20 bars per side symmetric window = 80-bar horizon). Reducing lookback or switching to 1H may find more signals. However, BTC crypto in general trends too much for pure mean-reversion divergence to work on 4H.

## Grade: BAD (baseline — recommend testing on 1H ETH or with wider lookback before finetuning)

---
## Post-Finetune Results (150 trials)
| Metric | Baseline | Finetuned |
|---|---|---|
| Sharpe | -1.25 | -0.05 |
| Total Return | -30.65% | -1.13% |
| MDD | 31.33% | 8.30% |
| Win Rate | 22.58% | 45.71% |
| Trades | 31 | 35 |
| PF | 0.12 | 0.90 |

Finetune improved from catastrophic to nearly break-even, but **still negative**. The win rate improved (45.7%) but average win/loss ratio is poor (PF 0.90). Only 35 trades = too rare on 4H.

## Grade: BAD (post-finetune — structural issue confirmed. Recommend discard for BTC 4H.)
