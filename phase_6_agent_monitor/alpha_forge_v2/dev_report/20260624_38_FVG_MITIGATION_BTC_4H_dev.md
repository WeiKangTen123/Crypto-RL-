---
status: POOR
id: 38
class: FVGMitigationReversalStrategy
coin: BTC
timeframe: 4h
sharpe: 0.41
return: 56.49
MDD: 60.53
win_rate: 13.64
trades: 132
PF: 1.11
date: 2026-06-24
recommendation: FAIL
---

# Dev Report: FVGMitigationReversalStrategy (ID 38)

**Alpha Hypothesis:** Fair Value Gap (FVG) mitigation reversal — enter when price returns to fill a previously formed FVG, expecting mean-reversion momentum from institutional re-engagement zones.
**Strategy Type:** Mean Reversion / Order Flow
**Built by:** @alpha-developer
**Date:** 2026-06-24
**Registered:** `settings.py` ID 38

---

## 1. Baseline Performance

| Metric | Value |
|---|---|
| Sharpe Ratio | 0.41 |
| Total Return | +56.49% |
| Max Drawdown | 60.53% |
| Win Rate | 13.64% |
| Total Trades | 132 |
| Profit Factor | 1.11 |
| Monthly Trades | ~2.0/month |
| Period | 2021-01-01 → 2026-05-31 |
| Coin / Timeframe | BTC / 4h |
| Leverage | 10x |
| Risk per Trade | 10% |

---

## 2. Yearly Breakdown

| Year | Return | Notes |
|---|---|---|
| 2021 | +87.98% | Bull market lifted all trades |
| 2022 | -37.95% | Bear market — counter-trend entries devastating |
| 2023 | +30.24% | Recovery, but insufficient |
| 2024 | +9.34% | Very low activity |
| 2025 | +5.37% | Marginal gains |
| 2026 (Jan-May) | -10.58% | Negative in current bull run |

---

## 3. Bug Fix Applied

**Previous status:** 0 trades, MEDIOCRE — caused by uninitialized `df['signal']` column in `generate_signals()`. When `.loc[mask, 'signal'] = 1` was called on a new column with NaN-containing masks, the result was a float column with NaN entries. The BacktestEngine then crashed with `cannot convert float NaN to integer`.

**Fix applied:**
- Added `df['signal'] = 0` initialisation before `.loc` assignments
- Added explicit `.notna()` guards to both `long_mitigation` and `short_mitigation` masks to prevent NaN propagation from early-bar FVG fields

---

## 4. Known Weaknesses

- **60.53% MDD** — unacceptable. Nearly full capital wipeout in bear markets. No macro trend filter means the strategy enters short into bull runs and long into bear runs.
- **13.64% win rate** — far below FVG strategy baseline (~40-50%). The `tp_multiplier=7.79` sets TP at 7.79× gap width — rarely reached. Losses accumulate on every failed mitigation.
- **No trend filter** — FVG mitigation works best WITH trend direction, not against it. The strategy currently takes both long and short FVGs indiscriminately.
- **~2 trades/month** — too infrequent for reliable statistical assessment. 132 trades over 5.4 years is insufficient.
- **2026 negative** — the strategy is losing in the current market environment, suggesting regime mismatch.

---

## 5. Developer Recommendation

**Verdict: FAIL**

> FVGMitigationReversalStrategy is fundamentally broken in its current configuration. MDD of 60.53% and win rate of 13.64% are below all acceptable thresholds. The strategy concept is valid (FVG mitigation is a real institutional price behavior), but the implementation lacks:
>
> 1. **Macro trend filter** — only take long FVGs in uptrend, short FVGs in downtrend
> 2. **TP calibration** — `tp_multiplier=7.79` is too aggressive; values of 1.5-3.0× gap width are more realistic
> 3. **Frequency** — 2 trades/month is insufficient; consider including partial fills or lower timeframes
>
> Recommend a complete rebuild with EMA trend gate (e.g., price above EMA-200 for long FVGs only) and re-optimized TP multiplier before re-evaluation. Send to GRAVEYARD until rebuilt.

**Suggested Rebuild Priority Params:** add `ema_trend_period` (200), reduce `tp_multiplier` to 1.5–3.0, add `use_trend_filter` flag.
