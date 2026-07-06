# Dev Report — HMMRegimeClassifierStrategy (ID 188)

**Date:** 2026-07-03  
**Factor Card:** `factor_library/Trend/20260622_hmm_regime_classifier.md`  
**Strategy File:** `strategy_backtest/strategies/hmm_regime_classifier_strategy.py`  
**Grade:** BAD

---

## Summary

Implements a 3-state Gaussian Hidden Markov Model fitted on (log_return, normalized_ATR) features
to classify each bar as Bearish (0), Sideways (1), or Bullish (2). Enters long in Bullish state with
Close > EMA(50) confirmation; short in Bearish state with Close < EMA(50). Exits on regime flip to
opposite direction or ATR trailing stop.

## Architecture

- **Library function:** `calc_hmm_regime_classifier(df, n_states=3)` added to `strategy_backtest/library.py`
- **HMM:** `hmmlearn.hmm.GaussianHMM`, covariance_type='full', n_iter=100, random_state=42
- **Features:** log_return (Close-to-Close) + norm_ATR (ATR14 / Close)
- **State labeling:** sort raw states by mean log return → 0=Bearish, 1=Sideways, 2=Bullish
- **Entry:** Bullish regime + Close > EMA(ema_period); Bearish regime + Close < EMA(ema_period)
- **Exit:** regime flips to opposite (bearish exit for longs, bullish exit for shorts) + ATR trailing stop (2.5×) + initial SL (1.5×)

## Backtest Results (BTC/4h, 2021-01-01 → 2026-05-31)

| Metric | Value |
|--------|-------|
| Sharpe Ratio | -0.72 |
| Sortino Ratio | -1.02 |
| Max Drawdown | 84.79% |
| Total Return | -82.79% |
| Win Rate | 32.74% |
| Profit Factor | 0.71 |
| Total Trades | 391 |

**Yearly breakdown:** 2021 -43.2% | 2022 -4.3% | 2023 -26.3% | 2024 -27.3% | 2025 -41.5% | 2026 +0.8%

## Failure Analysis

The strategy underperforms consistently across all years. Root causes:

1. **In-sample regime fitting**: HMM fitted on full 5.5yr dataset with states derived from historical statistics. Regimes are statistically accurate but not forward-predictive — the "Bullish" state clusters past bull markets, not future ones.

2. **Low win rate (32.74%)**: Regime transitions are noisy; the conflict-exit logic (long exits when bearish regime fires) causes many premature exits at losses before the trade has time to develop.

3. **Trailing stop interaction**: On 4H bars, the 2.5× ATR trail is tight enough relative to regime shift frequency that many trades hit SL before the regime confirms direction.

## Verdict

**BAD** — Theoretical HMM regime edge does not translate to profitable signals on BTC/4H.
The in-sample fitting introduces hindsight labeling that doesn't persist in live trading.
Possible rescue paths: rolling-window re-fit (true walk-forward), posterior probability gate (>60%),
or use as a meta-filter overlay rather than standalone entries.
