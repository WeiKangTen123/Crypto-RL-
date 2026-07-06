# Backtest Report — VolumeCapitulationReversalStrategy (ID 191)

**Grade:** BAD  
**Date:** 2026-07-03  
**Asset:** ETH/4H | Period: 2021-01-01 → 2026-05-31  
**Source:** 101 Formulaic Alphas — Alpha#43 (Kakushadze, WorldQuant 2015)

## Results (Post-Finetune)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | -1.04 |
| Sortino Ratio | -1.41 |
| Calmar Ratio | -0.39 |
| Total Return | -91.81% |
| Max Drawdown | 94.43% |
| Profit Factor | 0.91 |
| Win Rate | 19.79% |
| Total Trades | 950 |

## Yearly Returns

| Year | Return |
|------|--------|
| 2021 | -57.19% |
| 2022 | -52.27% |
| 2023 | -3.71% |
| 2024 | -52.12% |
| 2025 | +4.08% |
| 2026 | -16.44% |

## Key Params (Post-Finetune)
- adv_period=21, rank_v_period=39, momentum_period=12, rank_m_period=14
- signal_threshold=0.2124 (finetune lowered it; slower rank window is the real trade reducer)
- atr_trail_mult=4.60×, sl_atr_mult=1.12×

## Failure Analysis
- **Root cause**: Level-based signal fires broadly across many consecutive bars. Staying long
  while vol_rank × decline_rank > threshold during extended downtrends means re-entering
  (or holding through) multiple losing moves.
- **Win rate 19.79%**: Fundamentally insufficient. To break even at 0.1% fee per side,
  win rate needs to be ~30%+ at typical 2:1 reward-to-risk.
- **Fee drag severe**: $163 in fees in 2021 alone on 950-trade total.
- **Finetune couldn't fix**: Best Sharpe found was -1.04 after 200 trials. Structural
  over-trading is inherent to level-signal implementation of this alpha.

## Notes
Alpha#43 was designed cross-sectionally — on a single asset, there's no "universe mean"
to hedge against, so the always-in signal structure becomes a one-directional bet
that gets fee-destroyed. A crossover implementation (enter only when signal first rises
above threshold) may perform better in a future revision.
