# Crypto-RL — Algorithmic Crypto Trading Research Platform

A full-stack research platform for systematic cryptocurrency trading, combining **Deep Reinforcement Learning**, **classical quantitative strategies**, and an **agentic AI pipeline** that autonomously discovers, builds, and validates trading strategies.

---

## Architecture Overview

The system is split into two parallel research tracks:

```
TRACK A — Deep Reinforcement Learning
  Phase 0 → Phase 1 → Phase 2 → Phase 4 → Phase 5
   Data      Train    Validate  Backtest   PBO Check

TRACK B — Quantitative Strategy Research (Agentic)
  Phase 6 → Phase 7 → Phase 10 / Phase 11 / Phase 12
  Scan/Grade  Pattern   Pairs      Anti-Corr   Strategy Forge
              Mining    Trading    Crossover   (AI-built)
```

Both tracks are managed through a central **Flask dashboard** (`main_controller`) accessible from a browser.

---

## Phase 0 — Data Collection

**Purpose:** Download and preprocess all market data used across every phase.

**What it does:**
- Downloads 7+ years of OHLCV candles (4H timeframe) for BTC + macro tickers (ETH, DXY, SPY, VIX, JPY) from Binance and Yahoo Finance
- Computes **30 engineered features** per timestamp and saves them as NumPy arrays
- Stores spot OHLCV data for 5 coins (BTC, ETH, BNB, SOL, XRP) across 5 timeframes (5m, 15m, 1h, 4h, 1d) into Parquet files under `dataset/`

**30 Features breakdown:**
- **14 per-ticker:** close, volume, RSI, DX, UltOsc, OBV, ATR, Bband width, EMA ratio, log return + 4 raw OHLCV
- **15 cross-asset:** price ratio, volume ratio, 20-bar return correlation vs ETH / DXY / SPY / VIX / JPY
- **1 panic signal:** VIX log return

**Key files:** `phase_0/dl_trade_data.py`, `phase_0/dl_macro_data.py`, `phase_0/dl_trainval_data.py`

---

## Phase 1 — DRL Hyperparameter Optimization

**Purpose:** Train a Deep Reinforcement Learning agent and find the best hyperparameters using Bayesian optimization.

**What it does:**
- Uses **Optuna** to run 50 trials, each training a DRL agent and evaluating it on the validation split
- Objective metric: **Sharpe ratio** on the validation period
- Supports 3 cross-validation strategies:

| Script | Strategy | Description |
|---|---|---|
| `optimize_wf.py` | Walk-Forward | Single train → validate split |
| `optimize_kcv.py` | K-Fold CV | 5 rolling splits via scikit-learn |
| `optimize_cpcv.py` | **CPCV** | Combinatorial Purged Cross-Validation (López de Prado) — prevents look-ahead leakage |

**DRL algorithms available:** SAC · PPO · TD3 · DDPG · A2C (via local ElegantRL engine)

**Hyperparameters searched:** learning rate, batch size, gamma, network dimension, lookback window, reward normalisation weights, drawdown penalty, holding penalty

**Output:** `train_results/{run_name}/best_trial` + trained `actor.pth` model weights

**Key files:** `phase_1/optimize_cpcv.py`, `phase_1/optimize_kcv.py`, `phase_1/optimize_wf.py`

---

## Phase 2 — Statistical Validation

**Purpose:** Verify that the trained model's edge is statistically real, not luck.

**What it does:**
- Loads the Optuna study from Phase 1
- Computes mean Sharpe ± 95% confidence interval across all CV splits for DRL vs Buy-and-Hold
- Runs a **t-test**: is the DRL Sharpe significantly better than HODL?
- Generates an interactive HTML validation dashboard

**Why it matters:** A single good Sharpe number could be luck. The t-test across multiple time splits confirms the edge is consistent and reproducible.

**Key files:** `phase_2/validate.py`, `phase_2/validation_dashboard/`

---

## Phase 4 — Backtest Dashboard

**Purpose:** Run the trained DRL model on completely unseen out-of-sample data and visualise performance.

**What it does:**
- Loads `actor.pth` + best hyperparameters from Phase 1
- Runs inference: `state → actor.forward() → action → environment.step()`
- Computes: Sharpe, Sortino, Max Drawdown, Win Rate, Cumulative Return vs Buy-and-Hold
- Runs **Deep Validation** (26-rule rulebook) on any registered strategy:
  - Tier 1 Fatal Gates: min trades, cost ratio, regime survival, lookahead probe
  - Tier 2 Quality: WFO efficiency, IS→OOS decay, DSR p-value, random-label control
  - Tier 3 Warnings: bootstrap CI, param sensitivity, truncation test
  - Crypto Pack: funding cost, news event survival, vol regime

**Dashboard tabs:** Overview · Equity Curve · Drawdown · Trade Log · Rulebook · Deep Validation

**Key files:** `phase_4/backtest.py`, `phase_4/dashboard/`

---

## Phase 5 — PBO (Probability of Backtest Overfitting)

**Purpose:** Mathematically quantify whether the best strategy was selected by skill or luck.

**What it does:**
- Uses the CPCV framework (López de Prado & Bailey) on all trial return paths
- Forms all possible train/test split combinations
- Measures how often the best in-sample trial is also best out-of-sample
- **PBO < 0.5** → genuine edge | **PBO > 0.5** → likely data mining bias

**Key files:** `phase_5/pbo.py`, `phase_5/dashboard/`

---

## Phase 6 — Agentic Strategy Monitor

**Purpose:** Central command center that scans, grades, and manages all 157 quantitative strategies.

**What it does:**
- Scans every strategy in `strategy_backtest/settings.py` and runs a full backtest
- Grades each result: **GOOD** (Sharpe ≥ 1.0, DD < 35%, PF ≥ 1.2, ≥ 100 trades) / **MEDIOCRE** / **BAD**
- Displays a live dashboard with grade distribution, per-strategy metrics, and failure reasons
- Houses the **Alpha Forge v2** agent pipeline:
  - `@alpha-researcher` — discovers new strategy ideas from arXiv, TradingView, GitHub
  - `@alpha-developer` — implements discovered ideas as Python strategy classes
  - `@crypto-strategy-tuner` — fine-tunes BAD/MEDIOCRE strategies with Optuna
  - `@crypto-fullstack` — maintains the Flask server and dashboards
  - `@alpha-researcher`, `@crypto-data-engineer`, `@crypto-qa-tester` — supporting roles

**Scan modes:** Full Scan · Scan New (only unregistered IDs) · Force Rescan

**Key files:** `phase_6_agent_monitor/`, `.gemini/skills/`, `strategy_backtest/settings.py`

---

## Phase 7 — Recursive Pattern Mining

**Purpose:** Mine historical market data across multiple time windows to build a regime-aware "Wisdom Matrix".

**What it does:**
- Iterates through Micro (1 month), Meso (3 month), and Macro (1 year) windows
- For each window, identifies the optimal strategy parameters for that specific market regime
- Classifies regimes: TREND_UP, TREND_DOWN, CHOP_VOL, RANGE, etc.
- Outputs `wisdom_matrix.csv` — a knowledge base mapping `(regime, window) → best_params`

**Status:** Pattern mining pipeline is built. The `@crypto-pattern-agent` that uses the wisdom matrix for live paper trading is planned but not yet implemented.

**Key files:** `phase_7/miner.py`, `phase_7/scripts/`, `phase_7/data/`

---

## Phase 9 — Agentic Pipeline Flow Visualiser

**Purpose:** Visual map of the entire agentic research pipeline — how agents collaborate, message each other, and hand off work.

**What it does:**
- Interactive browser dashboard showing the end-to-end flow from alpha discovery → implementation → validation → deployment
- Shows agent roles, collaboration paths, and current pipeline status (GOOD/MEDIOCRE/BAD strategy counts)
- Tabs: Pipeline Flow · Agents · Scenarios · Reference

**Key files:** `phase_9_flow/index.html`, `phase_9_flow/app.js`

---

## Phase 10 — Quantitative Pairs Trading (Cointegration)

**Purpose:** Exploit statistical relationships between cointegrated crypto asset pairs using a Z-score mean reversion strategy.

**Core math:**
```
log(P_A) = α + β × log(P_B) + ε     (OLS hedge ratio)
Spread   = ε  (OLS residual)
Z-score  = (Spread - μ) / σ          (rolling normalisation, ZSCORE_WINDOW=48)
```

**How it works:**
1. Fits OLS regression to find hedge ratio β (requires R² ≥ 0.80)
2. Runs ADF cointegration test — only trades pairs that pass
3. Waits for Z-score to reach ±2.5σ **and** start reverting (CONFIRM_TURN)
4. Enters: Long the underperformer, Short the overperformer
5. Exits when Z → 0 (mean reversion complete) or Z ≥ 8.0σ (stop loss)

**Best config:** OLS_WINDOW=120, ZSCORE_WINDOW=48, MIN_ENTRY_Z=2.5, Z_STOP_LOSS=8.0, MIN_R2=0.80 → **+11.48% total ROI**

**Dashboard tabs:** Overview · Spread Chart · Trade Log · Equity · Correlation · Workflow (formula reference)

**Key files:** `phase_10/engine.py`, `phase_10/backtest.py`, `phase_10/dashboard/`

---

## Phase 11 — Anti-Correlation Crossover (Momentum Rotation)

**Purpose:** Trade pairs of assets that move in opposite directions — long the rising asset, short the falling one, entering at the exact moment momentum shifts.

**Core math:**
```
S[i] = (P_A[i]/P_A[i-N] - 1) - (P_B[i]/P_B[i-N] - 1)   (rolling relative performance spread)
Entry: S crosses zero after prior divergence ≥ MIN_DIVERGENCE (0.14) for ≥ MIN_PEAK_BARS
S_trade = ret_A - ret_B since entry  (measures P&L directly)
```

**How it works:**
1. Tracks rolling N-bar return spread between Asset A and Asset B
2. Waits for prior divergence (one clearly outperforming the other)
3. Enters at the **zero crossing** — the exact point momentum shifts
4. Long the previous underperformer, Short the previous outperformer
5. Exits at PROFIT_TARGET (12%), HARD_STOP (15%), or recross in wrong direction

**Best config:** NORM_WINDOW=120h, MIN_DIV=0.14, PROFIT=0.12, RECROSS=0.05 → **+83.83% total ROI**, all IS/OOS periods positive

**Dashboard tabs:** Spread · Price · Correlation · Equity · Phase · Log · Rulebook · Workflow

**Key files:** `phase_11/engine.py`, `phase_11/backtest.py`, `phase_11/dashboard/`

---

## Phase 12 — Strategy Forge (AI-Built Strategies)

**Purpose:** A modular strategy construction system where AI agents compose novel strategies from reusable signal building blocks, then Optuna fine-tunes the parameters.

**Architecture:**
```
Entry Signals  +  Filter Signals  +  Exit Methods  →  ForgeStrategy
(how to enter)    (conditions)        (how to exit)     (composed)
```

**Available building blocks:**

| Type | Examples |
|---|---|
| **Entry signals** | `ema_cross`, `bb_breakout`, `cvd_cross`, `taker_momentum`, `williams_r_reversion`, `tip_breakout` |
| **Filter signals** | `htf_ema_trend`, `adx_trend`, `atr_expansion`, `rsi_not_extreme`, `wr_not_extreme`, `htf_supertrend` |
| **Exit methods** | `chandelier_tp`, `atr_tp_sl_hold`, `psar_trail` |

**Pipeline (8 stages):**
1. INGEST — read alpha card, verify library functions exist
2. BUILD — compose strategy from building blocks
3. SYNTAX — AST static check
4. SMOKE — signal sanity check on 1-month data
5. DEV_REPORT — baseline backtest, register in `settings.py`, run Optuna fine-tune
6. WFO_EVO — 4-window walk-forward stability test
7. PBO_AUDIT — overfitting audit (threshold PBO < 0.40)
8. MANIFEST — final scan + classify + Obsidian sync + notify fullstack

**Best strategy:** #125 — 854% ROI | Strategy #142 (ETH 1H EMA Cross) — Sharpe 1.91, ROI 195.9%, MDD 8.8%, 218 trades

**Key files:** `strategy_forge/signals/`, `strategy_forge/composer/`, `phase_12/dashboard/`

---

## Strategy Library

**157 registered strategies** across 5 coins × 5 timeframes.

| Coin | Timeframes |
|---|---|
| BTC, ETH, BNB, SOL, XRP | 5m, 15m, 1h, 4h, 1d |

**Strategy classes include:** EMA Crossover, RSI Mean Reversion, VWAP ATR Reversion, Supertrend Pro, Liquidity Sweep Reversal, Order Block SMC, ICT Holy Trinity, WaveTrend MFI, Lorentzian Classification, Z-Score Stat Arb, Fisher Transform, ForgeStrategy (AI-composed), and 30+ more.

Grades are maintained in `.gemini/skills/crypto-strategy-tuner/data/scan_results.json`.

**Key files:** `strategy_backtest/settings.py` (registry), `strategy_backtest/strategies/` (implementations), `strategy_backtest/library.py` (shared math factors)

---

## Main Controller — Flask Dashboard

**Purpose:** Central web UI that launches and monitors every phase from a browser.

**Port:** `5001`  
**Start:** `bash start_server.sh`

**API routes include:**
- `GET /api/strategies` — full strategy list with scan grades
- `POST /api/run_backtest` — run backtest for a strategy
- `GET /api/validate_strategy?strategy_id=X` — run 26-rule deep validation
- `GET /api/scan_summary` — live grade counts
- `POST /api/force_rescan` — trigger full strategy rescan

**Key files:** `main_controller/main.py`

---

## Tech Stack

| Layer | Technology |
|---|---|
| **DRL Training** | PyTorch · ElegantRL (local) · SAC · PPO · TD3 |
| **Hyperparameter search** | Optuna (Bayesian, TPE sampler) |
| **Technical indicators** | TA-Lib (C-backed), custom library.py |
| **Statistical validation** | scipy · statsmodels · t-test · CPCV · PBO |
| **Data** | Binance API · CCXT · pandas · parquet |
| **Web dashboard** | Flask · vanilla JS · Canvas API |
| **AI agents** | Google Gemini 2.5 Flash / Pro via agy CLI |
| **Strategy fine-tuning** | Optuna (per-strategy, 100–200 trials) |

---

## Data Sources

- **Crypto OHLCV:** Binance (spot + futures) via `python-binance`
- **Macro:** Yahoo Finance (DXY, SPY, VIX, JPY) via `yfinance`
- **Order book depth:** Binance Vision historical archives

---

## Project Structure

```
Crypto-RL/
├── main_controller/          # Flask API server
├── strategy_backtest/        # 157-strategy registry + backtest engine
│   ├── settings.py           # Strategy library (all configs + params)
│   ├── strategies/           # Individual strategy class files
│   ├── library.py            # Shared math factors (RSI, VWAP, etc.)
│   └── validator.py          # 26-rule deep validation engine
├── strategy_forge/           # Modular AI-composed strategy system
│   └── signals/              # Entry / filter / exit building blocks
├── phase_0/                  # Data collection scripts
├── phase_1/                  # DRL training + Optuna optimization
├── phase_2/                  # Statistical validation dashboard
├── phase_4/                  # Backtest + deep validation dashboard
├── phase_5/                  # PBO analysis
├── phase_6_agent_monitor/    # Strategy scan/grade + Alpha Forge v2
├── phase_7/                  # Recursive pattern mining
├── phase_9_flow/             # Agentic pipeline visualiser
├── phase_10/                 # Pairs trading (cointegration)
├── phase_11/                 # Anti-correlation crossover
├── phase_12/                 # Strategy Forge dashboard
├── .gemini/skills/           # AI agent skill definitions + data
├── core/                     # ElegantRL DRL engine + environments
├── factor_library/           # Alpha idea cards (Markdown)
├── docs/                     # Documentation
└── requirements.txt          # Python dependencies
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add API keys
cp .env.example .env   # fill in BINANCE_API_KEY, BINANCE_SECRET

# 3. Start the dashboard
bash start_server.sh   # opens at http://localhost:5001
```

---

## Safety Notes

- **No API keys are committed** — `.env`, `binance_api.txt`, `open_router_API.txt`, `reddit_api.txt` are all git-ignored
- **No large data files are committed** — `dataset/` (6.5 GB), `train_results/` (11 GB), `venv/` are git-ignored
- **settings.py is write-guarded** — any script that modifies `settings.py` checks that no strategy IDs are dropped before writing, and keeps 5 timestamped snapshots in `strategy_backtest/.settings_snapshots/`
