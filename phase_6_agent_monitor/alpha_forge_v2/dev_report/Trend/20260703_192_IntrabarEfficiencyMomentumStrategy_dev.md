# Dev Report — IntrabarEfficiencyMomentumStrategy (ID 192)

**Date:** 2026-07-03  
**Source Alpha:** WorldQuant Alpha#101 — `(close - open) / (high - low + 0.001)`  
**Final Grade:** MEDIOCRE (Sharpe 0.32 post-finetune, 60 trades)

## Concept
Alpha#101 is the simplest WorldQuant formula: it measures how much of a bar's full
range (high-low) was captured as net directional move (close-open).

    +1.0 = open at low, close at high  (perfectly bullish)
    -1.0 = open at high, close at low  (perfectly bearish)
     0.0 = indecisive (doji, inside bar)

When smoothed over N bars and above a threshold, it signals sustained directional
momentum — the market is consistently printing strong bullish/bearish candles.

## Implementation
```python
hl_range = (high - low).clip(lower=1e-8)
bar_eff  = (close - open) / hl_range          # per-bar efficiency [-1, +1]
smooth   = bar_eff.rolling(smooth_period).mean()  # N-bar average
ema      = close.ewm(span=ema_period).mean()      # long-term trend gate

long  when smooth > threshold AND close > ema
short when smooth < -threshold AND close < ema
```

## Finetune Result
| Metric | Initial | Post-Finetune |
|--------|---------|---------------|
| Sharpe | -3.22 | +0.32 |
| Trades | 2293 | 60 |
| Win Rate | 30.40% | 36.67% |
| MDD | 99.99% | 16.23% |
| Total Return | -99.99% | +19.74% |

Key fixes:
- entry_threshold: 0.12 → 0.35 (3× tighter — only genuine momentum bursts trigger)
- ema_period: 50 → 179 (very long trend gate — BTC must be well above 7.5-day average)

## Strengths
- Lowest MDD in Alpha-series library (16.23%) — very capital-efficient
- 4/6 years positive; consistent small gains 2021-2024
- Profit factor 1.36 shows genuine per-trade edge

## Weaknesses
- 60 trades over 5.5 years → statistically thin; borderline confidence
- Annual returns modest (2-14%); needs more trades to compound meaningfully
- Both 2025 and 2026 slightly negative

## Verdict
MEDIOCRE — genuine edge, but highly selective. The strategy trades only during rare
sustained momentum bursts on BTC 1H when price is well above a slow trend line.
The signal quality is high but volume is low.

**Potential improvement**: relax ema_period slightly (150 vs 179) or try on ETH 1H
where volatility may generate more qualifying entry signals.
