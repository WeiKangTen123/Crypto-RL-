# Backtest Report — IntrabarEfficiencyMomentumStrategy (ID 192)

**Grade:** MEDIOCRE  
**Date:** 2026-07-03  
**Asset:** BTC/1H | Period: 2021-01-01 → 2026-05-31  
**Source:** 101 Formulaic Alphas — Alpha#101 (Kakushadze, WorldQuant 2015)

## Results (Post-Finetune)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 0.32 |
| Sortino Ratio | 0.47 |
| Calmar Ratio | 0.21 |
| Total Return | +19.74% |
| Max Drawdown | 16.23% |
| Profit Factor | 1.36 |
| Win Rate | 36.67% |
| Total Trades | 60 |

## Yearly Returns

| Year | Return |
|------|--------|
| 2021 | +2.71% |
| 2022 | +2.69% |
| 2023 | +6.59% |
| 2024 | +14.43% |
| 2025 | -3.16% |
| 2026 | -3.89% |

## Key Params (Post-Finetune)
- smooth_period=13, entry_threshold=0.3529 (was 0.12 → 3× tighter)
- ema_period=179 (very long trend filter — ~7.5 days on 1H)
- atr_trail_mult=3.56×, sl_atr_mult=1.94×

## Notable Strengths
- **Lowest MDD in Alpha# library**: 16.23% drawdown is exceptional for leveraged crypto
- **4/6 years positive**: 2021-2024 all green; 2025-2026 small negatives
- **Profit Factor 1.36**: Meaningful edge per trade (36% better on wins vs losses)
- **Near-zero fees**: Only 60 trades → fee pressure minimal

## Weaknesses
- **Only 60 trades**: Below GOOD threshold of 100. Statistical confidence is lower.
- **Annual return 2-14%**: Modest absolute returns. The large EMA period means we're
  mostly sitting out of the market waiting for rare high-efficiency momentum bursts.
- **2025-2026 negative**: Trend structure may have changed post-halving.

## Notes
Key fix: raising entry_threshold from 0.12 → 0.35 and extending ema_period to 179
eliminated the fee-killing 2293-trade problem. The strategy now trades only when BTC
bars are CONSISTENTLY bullish (average efficiency > 35% per bar over 13 bars) AND
price sits well above a nearly 8-day EMA. This selectivity preserves the edge but
creates very few entry opportunities.

Boundary: entry_threshold near upper range (0.35 of 0.03-0.40). Higher threshold
possible with wider range, but risks zero-trade periods.
