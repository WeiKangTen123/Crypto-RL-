---
id: 183
strategy: SupertrendProVolatilityStrategy
date: 2026-07-03
grade: BAD
status: BASELINE
---
# Dev Report: SupertrendProVolatilityStrategy (ID 183)

## Factor Card
`factor_library/Trend_Momentum/20260526_supertrend_pro_volatility.md`

## Logic
Supertrend flip entry filtered by:
- **Relative Volume** > 1.2× EMA(20) of volume (participation filter)
- **RSI zone**: 50–70 for longs, 30–50 for shorts (momentum not overbought)
- **Exit**: ATR trailing stop (3×) + Supertrend flip reversal

## Baseline Results (BTC 4H, 2021–2026, no finetune)
| Metric | Value |
|---|---|
| Total Return | -8.94% |
| Sharpe Ratio | 0.09 |
| Max Drawdown | 67.27% |
| Win Rate | 41.58% |
| Total Trades | 190 |
| Profit Factor | 0.97 |

| Year | Return |
|---|---|
| 2021 | +56.64% |
| 2022 | -0.91% |
| 2023 | -43.64% |
| 2024 | -3.64% |
| 2025 | +17.29% |
| 2026 | -7.89% |

## Analysis
RV + RSI zone filter reduces entry count vs plain Supertrend but doesn't meaningfully improve quality at defaults. 2023 drawdown (-43.6%) reflects Supertrend whipsaw in ranging market. MDD 67% is critical.

**Possible improvement via finetune:** wider st_multiplier (2.5–5.0) to reduce flips, higher rv_threshold (1.5+) for only strong-volume entries.

## Grade: BAD (baseline — no finetune)

---
## Post-Finetune Results (150 trials)
| Metric | Baseline | Finetuned |
|---|---|---|
| Sharpe | 0.09 | **0.92** |
| Total Return | -8.94% | **+348.91%** |
| MDD | 67.27% | 35.48% |
| Win Rate | 41.58% | 47.97% |
| Trades | 190 | 123 |
| PF | 0.97 | 1.42 |

**Key param changes:** rv_threshold 1.2→1.57 (stricter volume gate), rv_period 20→37 (smoother baseline), atr_trail_mult 3.0→4.68 (wider trail to let winners run).

## Grade: MEDIOCRE (post-finetune — Sharpe 0.92 < 1.0 threshold for GOOD)
