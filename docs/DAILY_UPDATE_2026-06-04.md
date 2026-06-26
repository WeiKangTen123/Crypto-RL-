# Daily Update — 2026-06-04

---

## System Changes Today

### Bug Fixes

#### SupertrendProStrategy (ID 99) — Runtime Crash Fixed
- **Problem**: Strategy was crashing with `TA_RSI` and `TA_ATR` errors mid-backtest
- **Fix 1** (10:30): Added `rsi_period` validation — negative values (e.g. -5) now clamp to 14
- **Fix 2** (10:45): Added data-length guard — talib calculations now skip bars where `len(df) < period`
- **Outcome**: Strategy re-added to scan library, re-graded at Sharpe 0.68

---

### Strategy Fine-Tunes — 5 Promoted Today

| ID | Strategy | Coin | TF | Sharpe Before | Sharpe After | Action |
|----|----------|------|----|--------------|-------------|--------|
| 65 | EMARibbonRSIMomentumStrategy | BTC | 1h | — | 2.10 | Promoted to leaderboard |
| 70 | SupertrendProStrategy | XRP | 4h | — | 1.07 | Promoted to leaderboard |
| 85 | SupertrendATRMomentumStrategy | BTC | 4h | — | 1.02 | Promoted to leaderboard |
| 17 | TakerEMAPullbackStrategy | BTC | 15m | — | 1.38 | Promoted + params updated in code |
| 18 | MACDKDJStrategy | BNB | 4h | — | 1.37 | Promoted + params updated in code |

#### Key Parameter Changes in Code

**`taker_ema_pullback_strategy.py` (ID 17)**
| Param | Old | New |
|-------|-----|-----|
| `ema_slow` | 200 | 193 |
| `taker_threshold` | 0.55 | 0.6405 |
| `sl_pct` | 0.05 | 0.1905 |
| `tp_rr` | 3.0 | 3.7837 |
| `swing_lookback` | 20 | 28 |

**`macd_kdj_strategy.py` (ID 18)**
| Param | Old | New |
|-------|-----|-----|
| `macd_fast / slow` | 12 / 26 | 26 / 31 |
| `macd_signal` | 9 | 20 |
| `kdj_period` | 9 | 29 |
| `kdj_oversold / overbought` | 30 / 70 | 35.0 / 84.0 |
| `stop_loss_pct` | 0.05 | 0.0905 |
| `trend_ema_period` | 200 | 226 |

---

### New Documentation Created (by Gemini agents)

| File | Summary |
|------|---------|
| `docs/DYNAMIC_MARKET_STRATEGIES.md` | Regime detection theory — HMM, ATR-based, order flow classification |
| `docs/recommendation/REGIME_AWARE_ENSEMBLE.md` | Full RAE system proposal — regime classifier + ensemble manager design |
| `docs/recommendation/ENSEMBLE_BACKTEST_FRAMEWORK.md` | Validation framework for ensemble strategies — purged OOS, lag stress test |

---

## Current Leaderboard (24 strategies)

| Rank | ID | Strategy | Coin | TF | Sharpe | Return | MDD | Note |
|------|----|-----------|----|----|----|--------|-----|------|
| 1 | 75 | T3NexusStiffStrategy | BTC | 1h | 3.40 | 502.3% | 17.4% | |
| 2 | 82 | HarmonicDivergenceStrategy | BTC | 4h | 3.27 | 99.2% | 8.6% | |
| 3 | 65 | EMARibbonRSIMomentumStrategy | BTC | 1h | 2.10 | 83.9% | 16.7% | **New** |
| 4 | 76 | MeanReversionFundingRateStrategy | BTC | 4h | 1.76 | 78.2% | 7.1% | Ranging |
| 5 | 16 | ETHLayeredReversionStrategy | ETH | 15m | 1.71 | 3109.8% | 89.7% | ⚠️ MDD |
| 6 | 86 | MultiTFMomentumReversalStrategy | BTC | 4h | 1.63 | 43.1% | 13.5% | |
| 7 | 48 | WaveTrendMFIDivergenceStrategy | BTC | 1h | 1.52 | 38.6% | 6.2% | |
| 8 | 17 | TakerEMAPullbackStrategy | BTC | 15m | 1.38 | 363.1% | 21.2% | **Tuned** |
| 9 | 18 | MACDKDJStrategy | BNB | 4h | 1.37 | 78.7% | 12.7% | **Tuned** |
| 10 | 85 | SupertrendATRMomentumStrategy | BTC | 4h | 1.02 | 142.5% | 26.4% | **New** |
| — | 70 | SupertrendProStrategy | XRP | 4h | 1.07 | 349.4% | 55.0% | **New** ⚠️ MDD |

---

## 2026 Market Analysis

Ran 2026-only backtests (Jan 1 → Jun 1) across 13 strategies from both GOOD and MEDIOCRE tiers to determine which are actually viable for paper trading now.

### Key Finding: 2026 Is a Ranging / Choppy Market

Trend-following momentum strategies — including the overall #1 ranked strategy — are **losing money** in 2026. Mean reversion and multi-timeframe filtering are winning.

### Full 2026 Results

| ID | Strategy | 2026 Sharpe | 2026 Return | MDD | Trades | Verdict |
|----|----------|------------|-------------|-----|--------|---------|
| 75 | T3NexusStiff BTC 1h | -1.04 | -21.70% | 51.77% | 51 | ❌ Overfitted to bull run |
| 65 | EMARibbonRSI BTC 1h | -0.39 | -6.75% | 27.05% | 34 | ❌ Failing in chop |
| 12 | VWAPATRReversion BTC 4h | -2.18 | -19.92% | 31.70% | 233 | ❌ High fee drag |
| 15 | DualEMAVolatility ETH 4h | -2.22 | -16.41% | 21.13% | 2 | ❌ |
| 50 | EMACrossover SOL 4h | 0.02 | -0.44% | 14.61% | 19 | ❌ Flat |
| 79 | MeanRevisionFunding BNB 4h | -1.90 | -6.17% | 9.45% | 3 | ❌ |
| 17 | TakerEMAPullback BTC 15m | 0.86 | +9.40% | 15.86% | 43 | 🟡 Below threshold |
| 82 | HarmonicDivergence BTC 4h | 1.18 | +10.10% | 8.91% | 29 | 🟡 Low PF (0.60) |
| 85 | SupertrendATRMomentum BTC 4h | 1.06 | +12.10% | 16.90% | 23 | ✅ Pass |
| 86 | MultiTFMomentumReversal BTC 4h | 1.43 | +16.58% | 9.26% | 118 | ✅ Best reliable |
| 76 | MeanRevisionFunding BTC 4h | 2.93 | +17.06% | 4.41% | 15 | ✅ Best metrics |

---

## Paper Trade Selection — 2026

Three strategies selected based on 2026-only performance. Strategies with good overall Sharpe but negative 2026 results (ID 75, 65) were explicitly excluded.

---

### 1. MultiTFMomentumReversalStrategy — BTC 4H
**Strategy ID:** 86 | **Grade:** GOOD | **Status:** 🟢 READY FOR PAPER TRADE

**Logic:** Multi-timeframe momentum confirmation with reversal detection on BTC 4-hour. Requires alignment across 1h and 4h momentum signals before entry. High trade frequency gives strong statistical confidence.

**Backtest (Full Period: 2023–2026)**

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 1.63 |
| Total Return | 43.1% |
| Max Drawdown | 13.5% |
| Win Rate | — |
| Total Trades | ~370+ |

**2026 Only (Jan–Jun)**

| Metric | Value |
|--------|-------|
| Sharpe Ratio | **1.43** |
| Return | **+16.58%** |
| Max Drawdown | **9.26%** |
| Trades | **118** |
| Profit Factor | **1.40** |

**Why selected:** Highest trade count (118) in 2026 — most statistically reliable pick. Consistent across full history and 2026 window. Clean MDD under 10%.

**Risk note:** MDD 9.26% — use max 8% portfolio allocation.

---

### 2. MeanReversionFundingRateStrategy — BTC 4H
**Strategy ID:** 76 | **Grade:** GOOD | **Status:** 🟢 READY FOR PAPER TRADE

**Logic:** Mean reversion triggered by extreme funding rate deviations on BTC 4-hour. Enters counter-trend when funding rate exceeds threshold bands, exits on normalisation. Regime-specific — built for ranging markets.

**Backtest (Full Period: 2020–2026)**

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 1.76 |
| Total Return | 78.2% |
| Max Drawdown | 7.1% |
| Total Trades | 52 |

**2026 Only (Jan–Jun)**

| Metric | Value |
|--------|-------|
| Sharpe Ratio | **2.93** |
| Return | **+17.06%** |
| Max Drawdown | **4.41%** |
| Trades | **15** |
| Profit Factor | **3.24** |

**Why selected:** Best risk-adjusted performance in 2026 by a large margin. Sharpe 2.93 and MDD 4.41% is exceptional. 2026's ranging market is exactly the regime this strategy is designed for.

**Risk note:** Only 15 trades in 2026 (low count) — use smaller allocation until trade sample builds. Max 6% portfolio allocation.

---

### 3. SupertrendATRMomentumStrategy — BTC 4H
**Strategy ID:** 85 | **Grade:** GOOD | **Status:** 🟢 READY FOR PAPER TRADE

**Logic:** Supertrend direction + ATR volatility filter on BTC 4-hour. Enters on Supertrend flip when ATR confirms meaningful volatility. Avoids false signals during low-volatility drift periods.

**Backtest (Full Period: 2021–2026)**

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 1.02 |
| Total Return | 142.5% |
| Max Drawdown | 26.4% |
| Total Trades | ~200+ |

**2026 Only (Jan–Jun)**

| Metric | Value |
|--------|-------|
| Sharpe Ratio | **1.06** |
| Return | **+12.10%** |
| Max Drawdown | **16.90%** |
| Trades | **23** |
| Profit Factor | **1.42** |

**Why selected:** Consistent performer — overall Sharpe and 2026 Sharpe are nearly identical (1.02 vs 1.06), which means it is not overfitted to any single period. Most "honest" strategy of the three.

**Risk note:** MDD 16.9% in 2026 — use max 5% portfolio allocation.

---

## Paper Trade Setup Summary

| # | ID | Strategy | Coin | TF | 2026 Sharpe | 2026 MDD | Allocation |
|---|----|----------|------|----|------------|----------|------------|
| 1 | 86 | MultiTFMomentumReversal | BTC | 4h | 1.43 | 9.26% | 8% |
| 2 | 76 | MeanReversionFundingRate | BTC | 4h | 2.93 | 4.41% | 6% |
| 3 | 85 | SupertrendATRMomentum | BTC | 4h | 1.06 | 16.90% | 5% |

**Total allocation:** 19% of paper portfolio
**Paper trade start date:** 2026-06-05
**Review date:** 2026-07-05 (30 days)

---

## Strategies Excluded and Why

| ID | Strategy | Reason |
|----|----------|--------|
| 75 | T3NexusStiff BTC 1h | Overall #1 but -21.7% in 2026, MDD 51.77% — overfitted to bull run |
| 65 | EMARibbonRSI BTC 1h | -6.75% in 2026 — trend-following broken in current chop |
| 70 | SupertrendPro XRP 4h | +21.4% but only 5 trades in 2026 — statistically unreliable |
| 20 | SupertrendPro BTC 4h | +20.1% but only 6 trades in 2026 — could be luck |
| 12 | VWAPATRReversion BTC 4h | -19.9% in 2026 with 233 trades — confirmed loser, high fees |

---

*Generated: 2026-06-04 | Crypto-RL System*
