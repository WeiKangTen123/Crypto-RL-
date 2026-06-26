---
status: REJECTED
id: 128
sharpe: 0.78
return: 163.0
MDD: 37.0
cause_of_death: Triple lagging confirmation — entries too late, 2022 loss -28%
---

# Autopsy Report: FORGE_ETH_AROON_VORTEX_EMA (ID 128)

## Cause of Death
Triple lagging indicator stack (Aroon crossover + Vortex trend + EMA macro) creates excessive confirmation lag. All three indicators confirm trend direction *after* the trend has established — entries occur late and near exhaustion points rather than at inception.

## What Worked
- TP:SL ratio of 5.86 (sl=0.97×ATR, tp=5.68×ATR) correctly sized for low-frequency, high-conviction trades
- 2024 and 2025 were profitable (+89%, +61%) in clear trending markets where lag is less costly
- Vortex Indicator itself is conceptually valid

## What Failed
- 2022 loss of -28% from entering into exhausted bear bounces after triple confirmation delay
- 33.8% win rate is below the threshold for a trend-following strategy at this R:R
- 94 trades over 4 years is insufficient for statistical confidence
- Aroon crossover already lags — stacking Vortex (also lagging) and EMA (also lagging) compounds the problem

## Key Learning
**Vortex Indicator validation:** VI+/VI- crossover is a valid trend confirmation signal but performs poorly when combined with other lagging signals. Its optimal use case is as a filter on a *leading* entry signal (e.g., FVG, CVD delta shift, or order flow imbalance). Recommended follow-up: test `fvg + vortex_trend + taker_confirm` composition.

## Recommendation
Archive this specific composition. The Vortex Indicator should be revisited in a future V3 search with faster entry signals.
