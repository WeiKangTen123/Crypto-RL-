# Daily Update — 2026-06-05

---

## Section 1 — Phase 7: Pattern Mining System (Bug Sweep & Rebuild)

### What Was Found

Ran a full audit of Phase 7's raw result files. Found **3 critical data bugs** affecting 749 out of 750 historical raw result files stored in `phase_7/data/raw_results/*.json`.

### What Phase 7 Does

Phase 7 is the **Pattern Mining** layer of the Crypto-RL pipeline. Its job is to systematically backtest every strategy across hundreds of different time windows and market regimes, then distil the results into a single structured dataset — the **Wisdom Matrix** (`phase_7/data/wisdom_matrix.csv`).

Each row in the Wisdom Matrix captures one backtested pattern:
- Which strategy ran, on which coin and timeframe
- The exact time window (start/end date)
- The market regime that window fell into (trending, ranging, volatile)
- The outcome: Sharpe, ROI, MDD, trade count, win rate, gross profit

This is not a one-time backtest. Phase 7 mines across rolling, expanding, and anchored windows — producing 750 pattern records across all strategy and regime combinations.

### What Phase 7 Is Preparing For

Phase 7 feeds directly into **Phase 8 (Machine Learning / Deep Reinforcement Learning)**.

- **Supervised learning**: The Wisdom Matrix becomes a labelled training set. Input features are market conditions and strategy parameters; the labels are Sharpe, ROI, and MDD. A model learns to predict which strategy and parameter set will perform best given the current market regime.
- **Reinforcement learning**: The Wisdom Matrix gives the DRL agent a structured prior. Instead of exploring randomly, the agent starts with patterns already proven to work in specific regimes — drastically reducing training time and improving early convergence.

**Phase 7 is the data preparation phase. Phase 8 cannot train without it.**

### What Was Found During Audit

A full audit of the 750 stored raw result files (`phase_7/data/raw_results/*.json`) found 3 data integrity issues — MDD stored as 0, financial metrics stored as 0, and win_rate format inconsistency between old and new code. All 750 files were patched and the Wisdom Matrix was fully regenerated.

---

### What Was Fixed

| File | Action |
|------|--------|
| `phase_7/scripts/patch_metrics.py` | **CREATED** — one-time patch script; recomputes MDD from `equity_curve`, financial metrics from `trades_detail`, normalises `win_rate` to string format for all 750 raw JSON files |
| `phase_7/miner.py` | **UPDATED** — added `CSV_COLS` constant to enforce canonical column order on every Wisdom Matrix save |
| `phase_7/dashboard/index.html` | **FIXED** — win_rate display now handles both float and string types |
| `main_controller/main.py` | **FIXED** — log file handle leak: `log_fh` was left open after `Popen()` call; now closed immediately after subprocess starts |

### Outcome

- Patch script ran successfully: **750/750 files patched**
- `phase_7/data/wisdom_matrix.csv` fully regenerated from patched files
- MDD values now correct: **mean MDD = 12.05%, max MDD = 53.84%**
- Wisdom Matrix is clean and consistent — ready for downstream use

---

## Section 2 — Phase 7 Purpose: ML / DRL Training Data

### What the Wisdom Matrix Is

`phase_7/data/wisdom_matrix.csv` is the **structured feature store for Phase 8 ML/DRL training**.

Each row represents one backtested pattern:

| Column | Description |
|--------|-------------|
| `strategy_id` | Which strategy produced the result |
| `category` | Strategy family (mean reversion, momentum, etc.) |
| `window_type` | Backtest window type (rolling, expanding, anchored) |
| `start_date` / `end_date` | The specific time window tested |
| `regime` | Market regime label for that window (trending, ranging, volatile) |
| `regime_score` | Quantified regime strength |
| `roi` | Return on investment for that window |
| `sharpe` | Sharpe ratio |
| `mdd` | Max drawdown — now correctly populated |
| `trades` | Number of trades |
| `market_features` | JSON blob of market conditions (volatility, trend strength, etc.) |
| `params` | Exact strategy parameters used |

### Why It Matters for Phase 8

Phase 8 (ML/DRL) will use this data in two ways:

1. **Supervised learning**: Input = (market_features + regime + params), Label = (sharpe, roi, mdd). Train a model to predict which strategy/params will perform best given current market conditions.
2. **Reinforcement learning**: The Wisdom Matrix gives the DRL agent a prior — instead of exploring randomly, it starts with patterns that are already known to work in specific regimes.

**750 records, now fully correct, are ready as training data.**

---

## Section 3 — Paper Trading: 7 Strategies Live on SignalHive

### Capital Allocation

| Total Capital | Active | Reserve |
|---|---|---|
| $1,000,000 | $200,000 | $800,000 |

Reserve kept at 80% to allow future strategies to be added without liquidating existing positions.

### Active Strategy Lineup

| SignalHive Name | ID | Script | Coin | TF | Seed | Leverage |
|---|---|---|---|---|---|---|
| s17-taker-ema-btc | 102 | `strat_17_paper.py` | BTC | 15m | $50,000 | 5× |
| s36-vwap-sol | 103 | `strat_36_paper.py` | SOL | 4h | $44,000 | 5× |
| s30-liq-sweep-btc | 104 | `strat_30_paper.py` | BTC | 4h | $40,000 | 10× |
| s76-funding-btc | 105 | `strat_76_paper.py` | BTC | 4h | $30,000 | 10× |
| s81-funding-xrp | 106 | `strat_81_paper.py` | XRP | 4h | $20,000 | 10× |
| s12-vwap-btc | 107 | `strat_12_paper.py` | BTC | 4h | $10,000 | 5× |
| s85-supertrend-btc | 108 | `strat_85_paper.py` | BTC | 4h | $6,000 | 10× |

**Leverage note:** s17, s36, s12 use 5× (not 10×) because their stop-loss distance is 15–20% from entry — at 10× leverage, liquidation fires before the SL triggers (~9.5% adverse move). Reduced to 5× to keep liquidation distance safely below SL.

---

### Strategy Backtest Results & Selection Rationale

#### s85 — SupertrendATRMomentumStrategy | BTC 4h | $6K | lev=10×

| Metric | Value |
|--------|-------|
| Sharpe | 1.02 |
| Return | +142.5% |
| MDD | 26.4% |
| Trades | 180 |
| Grade | GOOD |
| WFO-validated | Yes (Leaderboard rank 18) |

**Why selected:** Most consistent performer of the group. Full-period Sharpe (1.02) and 2026-only Sharpe (1.06) are nearly identical — this means it is not overfitted to any particular bull or bear phase. The "honest" baseline strategy.

---

#### s81 — MeanReversionFundingRateStrategy | XRP 4h | $20K | lev=10×

| Metric | Value |
|--------|-------|
| Sharpe | 1.01 |
| Return | +108% |
| MDD | 15.4% |
| Trades | 249 |
| Grade | GOOD |
| WFO-validated | Yes (Leaderboard rank 19) |

**Why selected:** Same funding-rate mean reversion logic as s76 but on XRP — provides coin diversification. Strong trade count (249) gives high statistical confidence. Designed for ranging markets, which is 2026's current regime.

---

#### s76 — MeanReversionFundingRateStrategy | BTC 4h | $30K | lev=10×

| Metric | Value |
|--------|-------|
| Sharpe | 1.76 |
| Return | +78.2% |
| MDD | 7.1% |
| Trades | 52 |
| Grade | MEDIOCRE (trade count < 100) |
| WFO-validated | Yes (Leaderboard rank 4) |
| 2026-only Sharpe | **2.93** |
| 2026-only Return | **+17.06%** |
| 2026-only MDD | **4.41%** |

**Why selected:** Best risk-adjusted performance in 2026 by a large margin — Sharpe 2.93 with MDD under 5%. Current market (ranging, choppy) is exactly the regime this strategy is designed for. Low trade count is a known limitation; allocation sized conservatively at $30K as a result.

---

#### s36 — VWAPATRReversionStrategy | SOL 4h | $44K | lev=5×

| Metric | Value |
|--------|-------|
| Sharpe | 1.50 |
| Return | +462.4% |
| MDD | 28.0% |
| Trades | 1,368 |
| Profit Factor | 1.35 |
| Grade | GOOD |
| WFO-validated | **No** |

**Why selected:** Highest trade count of all 7 strategies — 1,368 trades gives the strongest statistical base. Extends the VWAP reversion approach to SOL for diversification beyond BTC-only exposure. Strong Sharpe and PF.

**Risk note:** Not WFO-validated — performance may not hold across all market windows. Monitor closely.

---

#### s17 — TakerEMAPullbackStrategy | BTC 15m | $50K | lev=5×

| Metric | Value |
|--------|-------|
| Sharpe | 1.38 |
| Return | +363.1% |
| MDD | 21.2% |
| Trades | 271 |
| Grade | GOOD |
| WFO-validated | Yes (Leaderboard rank 9) |
| 2026-only Sharpe | 0.86 |
| 2026-only Return | +9.40% |

**Why selected:** Shorter timeframe (15m) generates more signals than 4h strategies. Highest seed allocation because of strong overall Sharpe and large trade sample. 2026 performance is below threshold (Sharpe 0.86) but still positive — monitor.

---

#### s12 — VWAPATRReversionStrategy | BTC 4h | $10K | lev=5×

| Metric | Value |
|--------|-------|
| Sharpe | 0.90 |
| Return | +86.3% |
| MDD | 24.6% |
| Trades | 1,470 |
| Grade | MEDIOCRE |
| WFO-validated | Yes (Leaderboard rank 21) |
| 2026-only Sharpe | **-2.18** |
| 2026-only Return | **-19.92%** |

**Why selected:** WFO-validated with the highest trade count overall (1,470). However, **2026 performance is clearly poor** — confirmed underperformer in current ranging/choppy conditions (high trade frequency is eating fees). Allocated at minimum seed ($10K) for monitoring purposes only. If negative trend continues after 30 days, this strategy should be removed.

---

#### s30 — LiquiditySweepReversalStrategy | BTC 4h | $40K | lev=10×

| Metric | Value |
|--------|-------|
| Sharpe | 1.64 |
| Return | +331.1% |
| MDD | 16.3% |
| Trades | 270 |
| Profit Factor | **0.81** |
| Grade | **BAD** |
| WFO-validated | **No** |

**Why selected:** User decision to include. High Sharpe (1.64) is notable, but PF 0.81 < 1.0 is a red flag — the average loss is larger than the average gain, meaning the strategy is fundamentally losing on a per-trade basis despite a high Sharpe (which can happen when a few large winners inflate the ratio).

**⚠️ Highest risk of all 7 strategies.** Not WFO-validated and Grade BAD. Will require close monitoring. If PF does not improve in live paper trading after 30 days, this strategy should be reviewed for removal.

---

### Architecture

- Shared utilities: `paper_trade/paper_base.py`
- Launch script: `paper_trade/run_all_traders.sh` (starts all 7 in background with per-strategy log files)
- Each script connects to OKX WebSocket for live candle data, calls SignalHive API to open/close/manage positions
- s17 and s30 also subscribe to OKX `trades` channel to accumulate real-time taker buy volume (required by their strategy logic)
- s76 and s81 poll OKX funding rate REST endpoint on each bar close

---

## Section 4 — SignalHive Cleanup

| Strategy | Action | Reason |
|----------|--------|--------|
| s75-t3nexus-btc | Archived | Parameters only valid for 2023–2024 bull run; fails in 2026 conditions (-21.7% in 2026) |
| s82-harmonic-btc | Archived | Taken down by user decision |
| macd-kdj-adx-4h | Archived | Decommissioned from active trading |

---

## Current Leaderboard (26 strategies)

| Rank | ID | Strategy | Coin | TF | Sharpe | Return | MDD | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | 75 | T3NexusStiffStrategy | BTC | 1h | 3.40 | 502.3% | 17.4% | |
| 2 | 82 | HarmonicDivergenceStrategy | BTC | 4h | 3.27 | 99.2% | 8.6% | |
| 3 | 65 | EMARibbonRSIMomentumStrategy | BTC | 1h | 2.10 | 83.9% | 16.7% | |
| 4 | 76 | MeanReversionFundingRateStrategy | BTC | 4h | 1.76 | 78.2% | 7.1% | Ranging |
| 5 | 16 | ETHLayeredReversionStrategy | ETH | 15m | 1.71 | 3109.8% | 89.7% | ⚠ MDD |
| 6 | 22 | SuperFVMAStrategy | BTC | 4h | 1.69 | 51.3% | 13.0% | |
| 7 | 86 | MultiTFMomentumReversalStrategy | BTC | 4h | 1.63 | 43.1% | 13.5% | |
| 8 | 48 | WaveTrendMFIDivergenceStrategy | BTC | 1h | 1.52 | 38.6% | 6.2% | |
| 9 | 17 | TakerEMAPullbackStrategy | BTC | 15m | 1.38 | 363.1% | 21.2% | Paper Trade |
| 10 | 55 | WaveTrendMFIDivergenceStrategy | ETH | 1h | 1.38 | 21.5% | 2.5% | |
| 11 | 18 | MACDKDJStrategy | BNB | 4h | 1.37 | 78.7% | 12.7% | |
| 12 | 10 | TIPBreakoutStrategy | BTC | 1h | 1.27 | 26.0% | 4.3% | |
| 13 | 1 | MACDKDJStrategy | BTC | 1d | 1.24 | 221.8% | 9.2% | ⚠Trades |
| 14 | 8 | MeanReversionVRSI | BTC | 1h | 1.15 | 11.0% | 1.5% | Ranging |
| 15 | 78 | MeanReversionFundingRateStrategy | ETH | 4h | 1.08 | 58.5% | 12.5% | Ranging |
| 16 | 70 | SupertrendProStrategy | XRP | 4h | 1.07 | 349.4% | 55.0% | ⚠ MDD |
| 17 | 43 | DynamicSwingAnchoredVWAPStrategy | BTC | 1h | 1.03 | 23.3% | 14.0% | |
| 18 | 85 | SupertrendATRMomentumStrategy | BTC | 4h | 1.02 | 142.5% | 26.4% | Paper Trade |
| 19 | 81 | MeanReversionFundingRateStrategy | XRP | 4h | 1.01 | 109.8% | 15.4% | Paper Trade |
| 20 | 2 | BB_Squeeze_Breakout_Strategy | BTC | 1h | 0.92 | 272.1% | 53.8% | ⚠ MDD |
| 21 | 12 | VWAPATRReversionStrategy | BTC | 4h | 0.92 | 90.1% | 24.6% | Paper Trade |
| 22 | 19 | ETHMomentumSqueezeStrategy | ETH | 4h | 0.79 | 182.5% | 72.5% | ⚠ MDD |
| 23 | 79 | MeanReversionFundingRateStrategy | BNB | 4h | 0.73 | 63.6% | 16.3% | Ranging |
| 24 | 20 | SupertrendProStrategy | BTC | 4h | 0.54 | 1.8% | 86.2% | ⚠ MDD |
| 25 | 80 | MeanReversionFundingRateStrategy | SOL | 4h | 0.52 | 44.4% | 35.5% | Ranging |
| 26 | 9 | BTCSwingEMAMACD | BTC | 4h | 0.51 | 34.5% | 34.6% | Trend |

---

## Watch List for Next 30 Days

| Strategy | Concern | Action if not resolved |
|----------|---------|----------------------|
| s30 (LiquiditySweep) | PF 0.81, not WFO-validated | Remove from paper trade if PF stays < 1.0 |
| s12 (VWAPReversion BTC) | 2026 Sharpe -2.18 | Remove if still losing after 30 days |
| s36 (VWAPReversion SOL) | Not WFO-validated | Run WFO validation; delist if it fails |

---

*Generated: 2026-06-05 | Crypto-RL System*
