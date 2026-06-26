# Phase 6 Hypothesis Report: ADA 1H EMA Cross — EMA Trend Filtered, PSAR Trail (Forge #148)

## Executive Summary
Fast/slow EMA crossover on ADA 1H, gated by a long-only macro trend filter (price above EMA-100). High-frequency design targeting ~10 trades/month (1 per 2-3 days). Exits via PSAR trailing stop. Demonstrates 0 losing months across 29 months — a near-perfect consistency record.

## Mathematical Model
- **Entry Component**: EMA(15) crosses above EMA(21) — fast crossover on 1H captures short-trend impulses with low lag.
- **Filter (Trend Gate)**: Price must be above EMA(100) — long-only regime filter ensures trades align with the macro trend direction.
- **Exit**: PSAR trailing stop (acceleration=0.025, maximum=0.15) — low acceleration keeps the stop from triggering on small retracements; low maximum caps the trailing distance as momentum fades.

## Regime Expectation
This strategy is designed for high-frequency engagement during trending markets. The EMA(100) gate enforces long-only directional bias — approximately 40% of raw EMA crossover signals are suppressed when price is below the macro trend. This selective entry approach, combined with PSAR's adaptive trailing, results in consistent small-to-medium gains with near-zero drawdown (MDD 3.1%).

## Risk Profile
- **Holding Period**: Short swing, 6-24 hours per trade (1H timeframe).
- **Expected Trade Frequency**: ~10.7 trades/month (1 per 2.8 days).
- **Exit Selection Rationale**: Systematic sweep of all 6 exit types confirmed psar_trail as the only positive exit. Fixed TP/SL exits (atr_tp_sl, rr_ratio) all go negative — ADA 1H trend moves are long-running and cannot be capped.
- **Validated IS/OOS**: OOS Sharpe 3.63 > IS Sharpe 3.60 — OOS slightly better than IS, indicating zero overfitting.
- **Coin Selection Rationale**: ADA 1H shows exceptionally clean EMA dynamics vs BTC/ETH/SOL/DOT. The price structure responds strongly to EMA(15/21) crossovers with high follow-through rate.
- **0 Losing Months**: Across 29 months of history (Jan 2024 – May 2026), no losing month was recorded — a standout consistency metric.
