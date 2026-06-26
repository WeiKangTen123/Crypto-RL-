---
status: MEDIOCRE
id: 38
sharpe: 0.23
return: 8.6
mdd: 66.1
win_rate: 13.6
trades: 132
pf: 0.98
---
# Stage 03 Backtest Report: FVGMitigationReversalStrategy (ID 38)

## Performance Table
- Sharpe: 0.23
- Return: 8.6%
- MDD: 66.1%
- Win Rate: 13.6%
- Trades: 132
- Profit Factor: 0.98

## Yearly Breakdown

| Year | Return | Notes |
|---|---|---|
| 2021 | +87.98% | Rode bull run passively |
| 2022 | -37.95% | Heavy drawdown in bear |
| 2023 | +30.24% | Partial recovery |
| 2024 | +9.34% | Slow, low-activity |
| 2025 | +5.37% | Near-flat |
| 2026 (Jan-May) | -10.58% | Negative in current period |

## Bug Fix Note
Previous report showed 0 trades (MEDIOCRE) due to a NaN-to-integer crash in `generate_signals` — `df['signal']` column was not initialized before `.loc` assignment. Bug fixed: signal column now initialised to 0 and NaN guards added to both long/short mitigation masks. Real trade count is 132.

## Stability & Robustness
MDD of 60.53% is unacceptable for deployment — nearly wipes out initial capital in bear markets. Win rate of 13.64% is far below typical FVG strategy baselines (~40-50%). The strategy fires infrequently (132 trades over 5.4 years = ~2 trades/month) and is heavily reliant on large winners to offset many small losses. Profit factor of 1.11 means the edge is minimal and will disappear under realistic slippage.

## Expert Commentary
FVG Mitigation Reversal on BTC 4H produces a positive total return (+56%) but is structurally unsound. MDD of 60% disqualifies it from paper trading. The 13.64% win rate is the core issue — the strategy enters on FVG retracements but does not filter for macro trend direction, leading to frequent counter-trend losses. The `tp_multiplier=7.79` creates large TPs that rarely hit while stops are tight (gap bottom/top), explaining the inverted win rate.

**Verdict: POOR — not suitable for paper trading. Needs trend filter, win rate improvement, and MDD reduction before re-evaluation.**
