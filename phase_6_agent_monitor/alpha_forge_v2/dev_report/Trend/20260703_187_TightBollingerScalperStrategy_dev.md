---
id: 187
strategy: TightBollingerScalperStrategy
date: 2026-07-03
grade: BAD
status: FINETUNED
---
# Dev Report: TightBollingerScalperStrategy (ID 187)

## Factor Card
`factor_library/Mean_Reversion/20260526_tight_bollinger_scalper.md`

## Logic
Tight BB (1.5std) close-back-inside confirmation + EMA-200 flat slope filter. TP at BB midline, SL at 2×ATR.

| Metric | Baseline | Finetuned |
|---|---|---|
| Sharpe | -5.86 | -5.65 |
| Return | -99.98% | -99.98% |
| MDD | 99.98% | 99.99% |
| WR | 48.75% | 47.41% |
| Trades | 3118 | 3124 |
| PF | 0.59 | 0.66 |

**Key params:** bb_std 1.5→1.95, ema_period 200→247, ema_slope_thresh 0.003→0.006

## Diagnosis
Structural failure — over-trading. Even with bb_std pushed to 1.95 (nearly standard 2.0) the strategy still generates 3124 trades. The "close-back-inside" logic fires on nearly every candle that touches the bands. BTC 1H has persistent trends that the EMA slope filter fails to gate out adequately. Fee drag (0.1%/side) at this trade frequency guarantees ruin.

**Recommended action:** Discard for BTC/ETH trending assets. Would need a different asset class (e.g., stablecoin spreads, mean-reverting pairs) to be viable.

## Grade: BAD (structural — discard)
