---
id: 184
strategy: DiamondTriangleBreakoutStrategy
date: 2026-07-03
grade: BAD
status: BASELINE
---
# Dev Report: DiamondTriangleBreakoutStrategy (ID 184)

## Factor Card
`factor_library/Volatility_Breakout/20260526_diamond_triangle_breakout.md`

## Logic
Volatility squeeze breakout: detect BB width contraction over N bars (squeeze), then trade breakout above/below BB when volume spikes (>1.5× EMA) and ADX confirms trend (>25).
- **Exit**: ATR trailing stop (3×) with initial hard SL at 1.5× ATR

## Baseline Results (BTC 4H, 2021–2026, no finetune)
| Metric | Value |
|---|---|
| Total Return | +2.14% |
| Sharpe Ratio | 0.10 |
| Max Drawdown | 21.68% |
| Win Rate | 29.89% |
| Total Trades | 87 |
| Profit Factor | 1.04 |

| Year | Return |
|---|---|
| 2021 | +4.97% |
| 2022 | -2.00% |
| 2023 | +4.56% |
| 2024 | +2.12% |
| 2025 | +4.47% |
| 2026 | -11.00% |

## Analysis
Positive total return and consistent (small) yearly gains except 2022 and 2026. Very low Sharpe at 0.10 — the win rate (30%) is too low because many squeeze breakouts fail. PF 1.04 is break-even.

**Best path forward:** finetune squeeze_pct (tighter squeeze = stronger signal), vol_spike_mult (higher = fewer but better entries), and adx_threshold. Consider using larger trail (5×) to let winners run.

## Grade: BAD (baseline — no finetune)

---
## Post-Finetune Results (150 trials)
| Metric | Baseline | Finetuned |
|---|---|---|
| Sharpe | 0.10 | **1.26** |
| Total Return | +2.14% | **+837.37%** |
| MDD | 21.68% | 28.24% |
| Win Rate | 29.89% | 39.23% |
| Trades | 87 | 209 |
| PF | 1.04 | 1.45 |

**Key param changes:** bb_period 20→13 (faster squeeze detection), bb_std 2.0→1.57 (tighter bands), squeeze_bars 5→3 (shorter squeeze window), atr_trail_mult 3.0→3.68.

## Grade: GOOD (post-finetune — Sharpe 1.26, 209 trades → PAPER_READY)
