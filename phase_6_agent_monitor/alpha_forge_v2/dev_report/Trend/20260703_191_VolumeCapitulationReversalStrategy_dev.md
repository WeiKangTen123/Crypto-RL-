# Dev Report — VolumeCapitulationReversalStrategy (ID 191)

**Date:** 2026-07-03  
**Source Alpha:** WorldQuant Alpha#43 — `ts_rank(volume/adv20,20) * ts_rank(-delta(close,7),8)`  
**Final Grade:** BAD (Sharpe -1.04 post-finetune)

## Concept
Alpha#43 detects capitulation: the product of "how unusually large is volume" ×
"how large was the recent price decline". When both are in the top percentile simultaneously,
the market is likely in a panic-selling phase → contrarian buy.

## Implementation
```python
vol_rank     = (volume / adv).rolling(rank_v_period).rank(pct=True)
decline_rank = (-close.diff(momentum_period)).rolling(rank_m_period).rank(pct=True)
buy_signal   = vol_rank * decline_rank   # peaks during capitulation
sell_signal  = vol_rank * rise_rank      # peaks during exhaustion
```

Long when buy_signal > threshold AND buy_signal > sell_signal.

## Finetune Result
| Metric | Initial | Post-Finetune |
|--------|---------|---------------|
| Sharpe | -3.39 | -1.04 |
| Trades | 1164 | 950 |
| Win Rate | 32.82% | 19.79% |

Key change: rank_v_period 20→39 (slower rank window = less frequent signals).
However threshold went DOWN 0.35→0.21 (optimizer favored more trades but with
longer rolling windows). Net: fewer trades but still win-rate failure.

## Root Cause Diagnosis
Level-signal design is incompatible with this alpha on a single asset:
- During downtrends, vol_rank AND decline_rank BOTH stay elevated for many bars
- This keeps signal=1 continuously → many re-entries eating fees
- Win rate collapses to 19.79% because we're always buying into falling markets

## Verdict
BAD — structural failure. The cross-sectional design of Alpha#43 (where other longs
offset this short-duration trade) doesn't translate to single-asset level signals.

**Potential fix**: Implement as crossover signal (enter only on first bar when signal
rises above threshold; exit via trailing stop; no re-entry for N bars).
