# Crypto-RL — Algorithmic Crypto Trading Research Platform

A full-stack research platform for systematic cryptocurrency trading, combining **Deep Reinforcement Learning (DRL)**, **classical quantitative strategies**, and a **multi-agent AI pipeline** (6 autonomous Gemini agents) that discovers, builds, fine-tunes, and validates trading strategies 24/7.

---

## Two Research Tracks

```
TRACK A — Deep Reinforcement Learning (DRL)
──────────────────────────────────────────────────────────────────
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 4 ──► Phase 5
 Data        Train       Validate    Backtest     PBO Check
 Collection  (Optuna+    (t-test,    (OOS eval,   (Overfitting
             CPCV)       95% CI)     26 rules)     probability)

TRACK B — Quantitative Strategy Research (Agentic)
──────────────────────────────────────────────────────────────────
Phase 6 ──► Phase 7 ──► Phase 10 / Phase 11 / Phase 12
Scan &       Pattern     Pairs        Anti-Corr    Strategy Forge
Grade        Mining      Trading      Crossover    (AI-built)
(6 agents)   (Wisdom     (Cointegr.   (Momentum    (Modular
             Matrix)      Z-score)     Rotation)    Composer)
```

Both tracks are managed from a central **Flask dashboard** (`main_controller`) on port **5001** — start with `bash start_server.sh`.

---

## Track A — Deep Reinforcement Learning Pipeline

---

### Phase 0 — Data Collection

**Purpose:** Download, clean, and preprocess all market data used across the DRL pipeline.

**Flow:**
```
Binance API / Yahoo Finance
        │
        ▼
dl_trade_data.py      → spot OHLCV Parquet files (5 coins × 5 timeframes)
dl_macro_data.py      → macro tickers (DXY, SPY, VIX, JPY)
dl_trainval_data.py   → 30-feature NumPy arrays for DRL training
        │
        ▼
dataset/{COIN}/{TF}/spot_ohlcv.parquet   (6.5 GB, git-ignored)
train_results/...price_array.pkl         (pickled NumPy arrays)
```

**30 Engineered Features:**
- **14 per-ticker:** close, volume, RSI, DX, UltOsc, OBV, ATR, Bband width, EMA ratio, log return + 4 raw OHLCV
- **15 cross-asset:** price ratio, volume ratio, 20-bar return correlation vs ETH / DXY / SPY / VIX / JPY
- **1 panic signal:** VIX log return

**Supported coins:** BTC, ETH, BNB, SOL, XRP
**Supported timeframes:** 5m, 15m, 1h, 4h, 1d

**Key files:** `phase_0/dl_trade_data.py`, `phase_0/dl_macro_data.py`, `phase_0/dl_trainval_data.py`

---

### Phase 1 — DRL Hyperparameter Optimization

**Purpose:** Train a DRL agent and find optimal hyperparameters using Bayesian optimization across multiple time splits.

**Flow:**
```
price_array.pkl + tech_array.pkl + time_array.pkl
        │
        ▼
Optuna (50 trials, TPE sampler)
        │
        ├── optimize_wf.py    → Walk-Forward (single train/val split)
        ├── optimize_kcv.py   → K-Fold CV (5 rolling splits, scikit-learn)
        └── optimize_cpcv.py  → CPCV — Combinatorial Purged Cross-Validation
                                       (López de Prado, most leak-proof)
        │
        ▼  each trial:
        Train DRL on train split → Evaluate on val split → Report Sharpe
        │
        ▼
train_results/{run_name}/
├── best_trial        (best hyperparams JSON)
├── stored_agent/
│   └── actor.pth     (trained model weights)
└── optuna_study.pkl  (full Optuna study)
```

**DRL Algorithms (via ElegantRL):** SAC · PPO · TD3 · DDPG · A2C

**Hyperparameters searched:**
```
learning_rate    batch_size       gamma            net_dimension
target_step      lookback         norm_cash        norm_stocks
norm_tech        norm_reward      norm_action      drawdown_weight
jitter_weight    holding_penalty
```

**Why CPCV:** Standard K-Fold leaks future information across time windows. CPCV purges overlapping data between folds, giving an unbiased estimate of out-of-sample performance.

**Key files:** `phase_1/optimize_cpcv.py`, `phase_1/optimize_kcv.py`, `phase_1/optimize_wf.py`, `phase_1/monitor_training.py`

---

### Phase 2 — Statistical Validation

**Purpose:** Confirm the trained model's edge is statistically significant — not luck.

**Flow:**
```
optuna_study.pkl (from Phase 1)
        │
        ▼
validate.py
├── Load all CV-split Sharpe ratios from best trial
├── Compute mean Sharpe ± 95% confidence interval (DRL vs Buy-and-Hold)
├── Run t-test: H₀ = DRL Sharpe ≤ HODL Sharpe
│   p < 0.05 → reject H₀ → edge is statistically real
└── Generate interactive HTML dashboard
        │
        ▼
phase_2/validation_dashboard/   (browser charts: CI bands, t-stat, p-value)
```

**Why it matters:** A single backtest Sharpe of 1.5 could be one lucky period. The t-test across multiple CPCV splits confirms the edge holds consistently across different market regimes.

**Key files:** `phase_2/validate.py`, `phase_2/validation_dashboard/`

---

### Phase 4 — Backtest & Deep Validation Dashboard

**Purpose:** Evaluate the trained DRL model on completely unseen out-of-sample data, and run a 26-rule rulebook on any registered strategy.

**Flow:**
```
actor.pth + best_trial (from Phase 1)
        │
        ▼
phase_4/backtest.py
├── Load CryptoEnvCCXT with trade data (2024–2026)
├── Inference loop: state → actor.forward() → action → env.step()
├── Compute: Sharpe, Sortino, Max Drawdown, Win Rate, Return vs HODL
└── Write results to phase_4/dashboard/data.js
        │
        ▼
phase_4/dashboard/   (interactive browser UI)
├── Overview tab      — summary metrics
├── Equity Curve tab  — cumulative return vs Buy-and-Hold
├── Drawdown tab      — underwater curve
├── Trade Log tab     — every entry/exit with P&L
├── Rulebook tab      — 26-rule pass/fail checklist
└── Deep Validation   — run full validator on any strategy (button)
```

**Deep Validation — 26 Rules (4 Tiers):**
```
Tier 0 — Prerequisites (2 rules)
  T0-01: Data integrity check (min 2000 bars, no NaN columns)

Tier 1 — Fatal Gates (10 rules)   ← ALL must pass for APPROVED
  T1-01: Sharpe Ratio ≥ 0.5
  T1-02: Total Return > 0
  T1-03: Max Drawdown < 50%
  T1-04: Win Rate ≥ 30%
  T1-05: Profit Factor ≥ 1.0
  T1-05b: Min trades ≥ max(30, 5×params)
  T1-06: Worst daily loss ≥ -20%
  T1-07: Cost ratio (fees/profit) < 50%
  T1-08: WFO Efficiency ≥ 0.5
  T1-09: Lookahead probe (shifted data Sharpe delta < 15%)
  T1-10: Regime survival (≥ 2/3 of bear/range/bull regimes positive)

Tier 2 — Quality Gates (6 rules)
  T2-01: WFO Efficiency ≥ 0.5
  T2-02: IS→OOS Sharpe decay ≤ 0.5
  T2-03: PBO < 0.50 (skip in quick mode)
  T2-04: DSR p-value < 0.05
  T2-05: Real Sharpe rank ≥ 95th percentile vs random-label shuffle
  T2-06: Monthly GTP ≥ 1.0 OR PF ≥ 1.5

Tier 3 — Warnings (5 rules)
  T3-01: Bootstrap 90% CI lower bound > 0
  T3-02: Param sensitivity < 15% Sharpe change (skip in quick mode)
  T3-03: Regime MDD < 50% in all tested regimes
  T3-04: Weekend/Weekday Sharpe ratio ≥ 0.30
  T3-05: Truncation test (50% / 75% data subsets remain stable)

Crypto Pack (3 rules)
  CR-01: Funding cost / net profit < 25%
  CR-02: Worst daily loss in LUNA/FTX/ETF events > -5%/day
  CR-03: Both low-vol and high-vol Sharpe > -0.5
```

**Verdict:** APPROVED (score ≥ 70% AND all T1 pass) · T1 FATAL FAIL · BELOW THRESHOLD

**Key files:** `phase_4/backtest.py`, `phase_4/dashboard/`, `strategy_backtest/validator.py`

---

### Phase 5 — PBO (Probability of Backtest Overfitting)

**Purpose:** Mathematically quantify whether the best strategy was chosen by skill or by data mining luck.

**Flow:**
```
All trial return paths (from CPCV splits in Phase 1)
        │
        ▼
pbo.py
├── Form all possible train/test split combinations (CPCV)
├── For each combination: rank trials in-sample vs out-of-sample
├── Count how often IS best trial is also OOS best trial
├── PBO = P(IS best is NOT OOS best)
│
├── PBO < 0.5  →  genuine edge (more likely skill than luck)
└── PBO ≥ 0.5  →  likely overfit (best trial was selected by luck)
        │
        ▼
phase_5/dashboard/   (ECDF plot, PBO heatmap)
```

**Key files:** `phase_5/pbo.py`, `phase_5/dashboard/`

---

## Track B — Quantitative Strategy Research

---

### Phase 6 — Agentic Strategy Monitor & Alpha Forge

**Purpose:** The central command center for Track B. Runs, grades, and manages all 157 registered strategies. Houses the 6 autonomous AI agents.

**Phase 6 Flow:**
```
strategy_backtest/settings.py  (157 strategies registered)
        │
        ▼
scan_all.py          → runs backtest for every strategy
classify_strategies.py → grades each result
        │
        ▼
scan_results.json    → GOOD / MEDIOCRE / BAD / ERROR per strategy
        │
        ▼
phase_6_agent_monitor/   (live browser dashboard)
├── Strategy list with grades, metrics, failure reasons
├── Scan New / Force Rescan buttons
├── Per-strategy detail: params, backtest results, deep validation
└── Alpha Forge v2 vault (agent-generated reports)
```

**Grading Thresholds:**
```
GOOD      → Sharpe ≥ 1.0  AND  MDD < 35%  AND  PF ≥ 1.2  AND  Trades ≥ 100
MEDIOCRE  → Sharpe ≥ 0.3  (misses one or more GOOD thresholds — tunable)
BAD       → Sharpe < 0.3  OR  MDD ≥ 85%  OR  PF = 0
ERROR     → strategy crashed during backtest
```

**Alpha Forge v2 Report Vault** (`phase_6_agent_monitor/alpha_forge_v2/`):
```
hypho_report/     → @alpha-researcher: scientific hypothesis reports (before build)
dev_report/       → @alpha-developer: development reports (after build + finetune)
backtest_report/  → @crypto-strategy-tuner: scan/grade reports for every strategy
autopsy_report/   → @alpha-developer: post-mortem for rejected strategies
elite_report/     → @crypto-strategy-tuner: market fit memos for GOOD strategies
```

**Key files:** `phase_6_agent_monitor/`, `.gemini/skills/`, `strategy_backtest/settings.py`, `strategy_backtest/run_backtest.py`

---

### Phase 7 — Recursive Pattern Mining

**Purpose:** Mine historical market data across multiple time horizons to build a regime-aware knowledge base mapping market conditions to optimal strategy parameters.

**Flow:**
```
Dataset (OHLCV Parquet files)
        │
        ▼
phase_7/miner.py --strategy_id {id}
        │
        ├── Generate time windows (Micro / Meso / Macro)
        ├── For each window:
        │   ├── classify_regime() → TREND_UP / TREND_DOWN / CHOP_VOL / RANGE
        │   └── optimize_window() → best params for this window + regime
        │
        ▼
phase_7/data/wisdom_matrix.csv
  strategy_id | window_id | type | start | end | params | roi | sharpe | regime | score
```

**Window Types:**
| Type | Duration | Purpose |
|---|---|---|
| Micro | 1 month | High-res local patterns, volatility spikes |
| Meso | 3 months | Medium-term phases, consolidation |
| Macro | 1 year | Full market cycles (Bull / Bear / Range) |

**Status:** Pattern mining is complete. The `@crypto-pattern-agent` that consumes the wisdom matrix for live paper trading is planned but not yet built.

**Key files:** `phase_7/miner.py`, `phase_7/scripts/regime_classifier.py`, `phase_7/scripts/window_tuner.py`

---

### Phase 9 — Agentic Pipeline Flow Visualiser

**Purpose:** Interactive browser map of the entire agentic research pipeline — how agents are connected, how they communicate, and the current state of the strategy library.

**What it shows:**
- End-to-end flow from alpha discovery → implementation → validation → deployment
- Live grade counts (GOOD / MEDIOCRE / BAD / total) loaded from `scan_results.json`
- Agent roles, inbox routing, collaboration paths

**Tabs:** Pipeline Flow · Agents · Scenarios · Reference

**Key files:** `phase_9_flow/index.html`, `phase_9_flow/app.js`, `phase_9_flow/styles.css`

---

### Phase 10 — Quantitative Pairs Trading (Cointegration Z-Score)

**Purpose:** Exploit long-run statistical equilibrium between cointegrated crypto pairs. When the spread diverges, trade mean reversion back to equilibrium.

**Core Math:**
```
Step 1 — OLS Hedge Ratio
  log(P_A) = α + β × log(P_B) + ε       (requires R² ≥ 0.80)

Step 2 — Spread
  Spread[i] = log(P_A[i]) - α - β × log(P_B[i])

Step 3 — ADF Cointegration Test
  H₀: spread is non-stationary (no cointegration)
  Pass: p-value < 0.05

Step 4 — OU Half-Life
  τ = -ln(2) / ln(ρ)   where ρ = autocorrelation of Δspread
  Valid range: 1 bar < τ < 100 bars

Step 5 — Z-Score
  Z[i] = (Spread[i] - μ_window) / σ_window   (ZSCORE_WINDOW = 48 bars)

Step 6 — Entry
  |Z[i]| ≥ MIN_ENTRY_Z (2.5σ)  AND  CONFIRM_TURN (Z starts reverting)
  → Long underperformer, Short overperformer

Step 7 — Exit
  Z → 0  (MEAN_REVERT)         → profit exit
  |Z| ≥ Z_STOP_LOSS (8.0σ)    → stop loss
```

**Entry/Exit Flow:**
```
Pair scanning (9 coins × C(9,2) = 36 pairs)
        │
        ▼
OLS fit → R² gate → ADF test → OU half-life check
        │  (fail → skip pair)
        ▼
Rolling Z-score monitor
        │
        ├── |Z| ≥ 2.5σ AND Z starts reverting → CONFIRM_TURN → ENTER
        │       Long A / Short B  (or reverse if Z > 0)
        │
        └── In trade:
            ├── Z → 0      → MEAN_REVERT exit (profit)
            ├── |Z| ≥ 8.0σ → Z_STOP_LOSS exit
            └── ZSTOP_CIRCUIT → pause pair after N consecutive stops
```

**Best Configuration:** OLS_WINDOW=120, ZSCORE_WINDOW=48, MIN_ENTRY_Z=2.5, Z_STOP_LOSS=8.0, MIN_R2=0.80 → **+11.48% total ROI**

**Dashboard Tabs:** Overview · Spread Chart · Trade Log · Equity · Correlation · Workflow (formula reference with demo chart)

**Key files:** `phase_10/engine.py`, `phase_10/backtest.py`, `phase_10/optimize.py`, `phase_10/dashboard/`

---

### Phase 11 — Anti-Correlation Crossover (Momentum Rotation)

**Purpose:** Trade pairs of assets moving in opposite directions — long the rising one, short the falling one — entering precisely when momentum shifts.

**Core Math:**
```
Step 1 — Rolling Relative Performance Spread
  ret_X(N) = P_X[i] / P_X[i-N] - 1          (N-bar return)
  S[i]     = ret_A(N) - ret_B(N)             (NORM_WINDOW = 120 bars)

Step 2 — Prior Divergence Guard
  S must reach ≥ MIN_DIVERGENCE (0.14) for ≥ MIN_PEAK_BARS before entry
  (prevents trading noise — requires meaningful prior separation)

Step 3 — Zero Crossing Entry
  S crosses zero from below → Long A / Short B
  S crosses zero from above → Long B / Short A
  Condition: prior divergence ≥ MIN_DIVERGENCE AND |S| < RECROSS_BUFFER

Step 4 — In-Trade Spread
  S_trade[i] = (P_A[i]/P_A[entry] - 1) - (P_B[i]/P_B[entry] - 1)
  (directly proportional to dollar P&L)

Step 5 — Exit
  S_trade ≥  PROFIT_TARGET (0.12)  → take profit
  S_trade ≤ -HARD_STOP_PCT (0.15) → emergency stop
  S_trade recrosses RECROSS_BUFFER (0.05) → false cross stop
  hold_bars ≥ MAX_HOLD_BARS       → time stop
```

**Entry/Exit Flow:**
```
All pair combinations (BTC, SOL, XRP, BNB, AVAX, ADA, DOT, LINK)
        │
        ▼
Rolling N-bar return spread S[i]
        │
        ├── |S| ≥ MIN_DIVERGENCE → divergence phase confirmed
        │
        └── S crosses zero → EXECUTE PAIR TRADE
                Long underperformer / Short outperformer
                │
                └── Monitor S_trade:
                    ├── ≥ +12% → PROFIT_TARGET exit
                    ├── ≤ -15% → HARD_STOP exit
                    ├── recross → FALSE_CROSS stop
                    └── timeout → TIME_STOP exit
```

**Best Configuration:** NORM_WINDOW=120, MIN_DIV=0.14, PROFIT=0.12, RECROSS=0.05 → **+83.83% total ROI**, all IS/OOS periods positive

**Dashboard Tabs:** Spread · Price · Correlation · Equity · Phase · Log · Rulebook · Workflow (formula reference with demo chart)

**Key files:** `phase_11/engine.py`, `phase_11/backtest.py`, `phase_11/rulebook.py`, `phase_11/dashboard/`

---

### Phase 12 — Strategy Forge (AI-Composed Strategies)

**Purpose:** Modular strategy construction system where AI agents compose novel strategies from reusable signal building blocks, then Optuna fine-tunes the parameters.

**Architecture:**
```
Entry Signal  +  Filter Signals (0–3)  +  Exit Method  =  ForgeStrategy
```

**Available Building Blocks:**

| Category | Available Signals |
|---|---|
| **Entry** | `ema_cross`, `bb_breakout`, `cvd_cross`, `taker_momentum`, `williams_r_reversion`, `tip_breakout` |
| **Filters** | `htf_ema_trend`, `adx_trend`, `atr_expansion`, `rsi_not_extreme`, `wr_not_extreme`, `htf_supertrend`, `zscore_gate` |
| **Exit** | `chandelier_tp`, `atr_tp_sl_hold`, `psar_trail` |

**Forge Pipeline:**
```
@alpha-researcher discovers idea
        │
        ▼  inbox: NEW_FACTOR_DISCOVERED
@alpha-developer — 8-Stage Build Process:
  [1/8] INGEST    → read candidate card, map math, verify library.py functions
  [2/8] BUILD     → compose ForgeStrategy with entry + filters + exit + Logic Switches
  [3/8] SYNTAX    → Python AST static check
  [4/8] SMOKE     → signal sanity check (count longs/shorts on 1-month data)
  [5/8] DEV_REPORT→ baseline → Optuna finetune → register in settings.py → dev report
  [6/8] WFO_EVO   → 4-window walk-forward stability test
  [7/8] PBO_AUDIT → overfitting audit (threshold PBO < 0.40)
  [8/8] MANIFEST  → scan + classify + Obsidian sync → notify @crypto-fullstack
        │
        ▼  (on fail at any stage)
  [!] AUTOPSY → write post-mortem, retain settings.py entry, notify @crypto-strategy-tuner
```

**Notable Strategies Built:**
- **#125** — Best ROI: 854%
- **#129** — FORGE_ETH_MTF_EMA_CROSS: Sharpe 1.12
- **#142** — FORGE_ETH_EMA_CROSS_1H: Sharpe 1.91, ROI 195.9%, MDD 8.8%, 218 trades (GOOD)

**Key files:** `strategy_forge/signals/entry_signals.py`, `strategy_forge/signals/filter_signals.py`, `strategy_forge/signals/exit_signals.py`, `strategy_forge/composer/`, `phase_12/dashboard/`

---

## The 6 Autonomous AI Agents

All agents run via `Crypto_Agent/agent_watcher.py`, which polls each agent's inbox every **30 seconds** and fires a scheduled task when idle.

```
python Crypto_Agent/agent_watcher.py <agent_id>
agent_id: fullstack | data | researcher | developer | qa | tuner
```

### Agent Schedules & Models

| Agent | ID | Scheduled Interval | Default Model |
|---|---|---|---|
| `@crypto-fullstack` | fullstack | Every 30 min | Gemini 2.5 Flash |
| `@crypto-data-engineer` | data | Every 60 min | Gemini 2.5 Flash |
| `@alpha-researcher` | researcher | Every 4 hours | Gemini 3.1 Pro Preview |
| `@alpha-developer` | developer | Every 60 min | Gemini 2.5 Flash |
| `@crypto-qa-tester` | qa | Every 60 min | Gemini 2.5 Flash |
| `@crypto-strategy-tuner` | tuner | Every 5 min | Gemini 2.5 Flash |

**Model Cascade** (quota fallback): `gemini-3.1-pro-preview` → `gemini-2.5-flash` → `gemini-2.5-flash-lite`

---

### Agent 1: @alpha-researcher — The Thinker

**Role:** Discover new alpha ideas from web sources and convert them into mathematical candidate cards.

**Pipeline (3 stages):**
```
[1/3] WEB_SEARCH
  Sources: GitHub, arXiv, SSRN, Quantpedia, TradingView scripts, Reddit r/algotrading
  Model: gemini-3.1-pro-preview (creative discovery stage)

[2/3] EXTRACT_ALPHA
  → Deconstruct article → extract core alpha premise
  → Apply 3 Institutional Guards:
      1. Poison Filter: check scan_results.json + autopsy_report/ for similar failed ideas
      2. Library-Aware Math: check library.py — don't reinvent existing indicators
      3. Data Universe Guard: only BTC/ETH/BNB/SOL/XRP on 5m/15m/1h/4h/1d
  → Write Candidate Card to factor_library/{CATEGORY}/

[3/3] HYPHO_REPORT & INDEX_SYNC
  → Write scientific hypothesis to phase_6_agent_monitor/alpha_forge_v2/hypho_report/
  → Sync Obsidian ledger
  → Send NEW_FACTOR_DISCOVERED inbox → @alpha-developer
```

**Scheduled task:** Alpha discovery cycle every 4 hours.
**Inbox messages handled:** `FINETUNE_PROMOTED`, `DATA_GAP`, `FACTOR_FAILURE_REPORT`

---

### Agent 2: @alpha-developer — The Builder

**Role:** Take candidate cards from the researcher and implement them as production-ready Python strategy classes.

**Pipeline (8 stages):**
```
[1/8] INGEST      → read card, extract coin/tf/date_from, verify library.py functions
[2/8] BUILD       → write strategy class with Logic Switches + regime guards
[3/8] SYNTAX      → Python AST static check + import verification
[4/8] SMOKE       → signal sanity (count longs/shorts) + 1-day execution test
[5/8] DEV_REPORT  → baseline → finetune (Optuna) → register settings.py → dev report
[6/8] WFO_EVO     → 4-window walk-forward stability test
[7/8] PBO_AUDIT   → overfitting check (PBO threshold 0.40)
[8/8] MANIFEST    → registration guard → scan + classify → Obsidian sync → notify fullstack

[!] AUTOPSY (on any failure)
  → write autopsy_report/, update factor_library/ status=REJECTED
  → KEEP settings.py entry (never delete)
  → notify @crypto-strategy-tuner via FACTOR_FAILURE_REPORT
```

**Inbox messages handled:** `NEW_FACTOR_DISCOVERED` → build | `STRATEGY_BUG` / `ZERO_TRADES` → fix
**Sends to:** `@crypto-fullstack` (after MANIFEST), `@crypto-strategy-tuner` (on AUTOPSY)

---

### Agent 3: @crypto-strategy-tuner — The Auditor

**Role:** Scan all registered strategies, grade them, fine-tune underperformers with Optuna, and generate market-fit reports for GOOD strategies.

**Pipeline (4 stages):**
```
[1/4] AUDIT
  → run check_registration.py (register any unregistered classes first)
  → load scan_results.json, identify PENDING / MEDIOCRE / ERROR targets

[2/4] WORK_CYCLE
  → scan_all.py   (runs all strategies, writes scan_results.json)
  OR
  → finetune.py --strategy_id {id}  (Optuna 100–200 trials on target strategy)

[3/4] REPORTING
  → generate Stage 03 Backtest Report to backtest_report/
  → Expert Commentary: trade character, chop warnings, hypothesis alignment

[4/4] MANIFEST
  → if GOOD: generate Market Fit Memo to elite_report/
  → sync Obsidian
  → notify @alpha-researcher via FINETUNE_PROMOTED (if Sharpe ≥ 1.0 reached)
```

**Grading Gates:**
```
GOOD      → Sharpe ≥ 1.0  AND  MDD < 35%  AND  PF ≥ 1.2  AND  Trades ≥ 100
MEDIOCRE  → Sharpe ≥ 0.3  (misses at least one GOOD threshold)
BAD       → Sharpe < 0.3  OR  MDD ≥ 85%  OR  every trade a loser
ERROR     → strategy crashed during scan
```

**Inbox messages handled:** `FINETUNE` (fine-tune specific ID), `GRADE_PENDING_NOW`, `FACTOR_FAILURE_REPORT`
**Sends to:** `@alpha-researcher` via `FINETUNE_PROMOTED`

---

### Agent 4: @crypto-fullstack — The Engineer

**Role:** Keep the Flask server and dashboards running. Fix UI/backend bugs. Monitor error logs.

**Pipeline (4 stages):**
```
[1/4] TRIAGE     → read error_log.jsonl, check server health (curl /api/strategy_list)
[2/4] IMPLEMENT  → patch main_controller/main.py or frontend JS/CSS
[3/4] CHAOS_TEST → run chaos_test.py (tests all 14+ Flask API routes)
[4/4] FINALIZE   → run sync_knowledge_base.py → regenerate KNOWLEDGE_BASE.md
                   → notify other agents if server was restarted
```

**Scheduled task (every 30 min):**
- Read error_log.jsonl for unprocessed errors
- Health check: `GET /api/strategy_list` → expect valid JSON
- Diagnose + fix if server returns 500 or is down
- Regenerate KNOWLEDGE_BASE.md

**Inbox messages handled:** `RUNTIME_ERROR_DETECTED`, `FLASK_ROUTE_FAIL`, `SETTINGS_IMPORT_FAIL`
**Key tools:** `scripts/chaos_test.py`, `scripts/zombie_sweep.py`, `scripts/sync_knowledge_base.py`

---

### Agent 5: @crypto-data-engineer — The Data Guardian

**Role:** Data quality, gap detection, and proactive health monitoring for all OHLCV Parquet files.

**Pipeline (4 stages):**
```
[1/4] SCAN    → audit integrity and freshness of all parquet files
[2/4] ANALYZE → identify gap patterns, dtype errors, stale data
[3/4] REPAIR  → run sync_all.py (Binance backfill) or repair_dtypes.py
[4/4] VERIFY  → final integrity check → update known_data_gaps.md
```

**Scheduled task (every 60 min):**
- Run `health_scout_v2.py` → check all 5 coins × 5 timeframes
- Log results to `HEALTH_SCOUT.log`
- Send `DATA_QUALITY_ISSUE` inbox to @alpha-researcher if gaps found
- Update `known_data_gaps.md` with affected coin/timeframe pairs

**Inbox messages handled:** `FUNDING_RATE_DATA_REPAIR_REQUEST`, `DATA_QUALITY_ISSUE`
**Key tools:** `scripts/sync_all.py`, `scripts/health_scout_v2.py`, `scripts/repair_dtypes.py`, `utility/fetch_multi_tf_data.py`

---

### Agent 6: @crypto-qa-tester — The Watchdog

**Role:** Automated QA — tests every Flask route, strategy import, and data linkage. Escalates failures to the right agent. Never fixes — only finds and routes.

**Pipeline (5 stages):**
```
[1/5] GROUP_1  → test all Flask API routes (14+ endpoints)
[2/5] GROUP_2  → verify strategy class imports + backtest engine integrity
[3/5] GROUP_3  → audit data linkage + smoke simulation (1-day backtest per strategy)
[4/5] GROUP_4  → registration audit (unregistered classes, settings/scan sync)
[5/5] FINALIZE → route failures:
                  Flask errors      → @crypto-fullstack
                  Strategy crashes  → @alpha-developer
                  Data gaps         → @crypto-data-engineer
                  Grade mismatches  → @crypto-strategy-tuner
```

**Scheduled task (every 60 min):** full system test suite
**Key tool:** `.gemini/skills/crypto-qa-tester/scripts/system_test.py`

---

## Agent Communication — Inbox System

Agents communicate by dropping JSON files into each other's `inbox/active/` folders.

```
Agent A                    Inbox System                    Agent B
   │                                                          │
   │  write JSON to:                                          │
   │  .gemini/skills/{agent-b}/inbox/active/                 │
   │  {timestamp}_{TOPIC}.json                               │
   │                                                          │
   │                     agent_watcher.py polls every 30s    │
   │                            │                            │
   │                            ▼                            │
   │                     drain_inbox() reads all             │
   │                     .json files in active/              │
   │                            │                            │
   │                            └──────────────────────► Agent B wakes + acts
   │                                                     moves file to dead_letter/
```

**Message Topics & Routing:**

| Topic | Sender | Receiver | Trigger |
|---|---|---|---|
| `NEW_FACTOR_DISCOVERED` | @alpha-researcher | @alpha-developer | New candidate card ready to build |
| `FINETUNE_PROMOTED` | @crypto-strategy-tuner | @alpha-researcher | Strategy reached Sharpe ≥ 1.0 |
| `FACTOR_FAILURE_REPORT` | @alpha-developer | @crypto-strategy-tuner | Strategy rejected at WFO/PBO |
| `FINETUNE` | @alpha-researcher | @crypto-strategy-tuner | Request to tune specific strategy ID |
| `STRATEGY_BUG` / `ZERO_TRADES` | @crypto-qa-tester | @alpha-developer | Strategy crashes or produces no signals |
| `FLASK_ROUTE_FAIL` | @crypto-qa-tester | @crypto-fullstack | Flask API endpoint returning error |
| `RUNTIME_ERROR_DETECTED` | @crypto-fullstack | @crypto-fullstack | Self-detected server error |
| `SETTINGS_IMPORT_FAIL` | @crypto-qa-tester | @crypto-fullstack | settings.py import broken |
| `DATA_QUALITY_ISSUE` | @crypto-data-engineer | @alpha-researcher | Gaps found in dataset |
| `FUNDING_RATE_DATA_REPAIR_REQUEST` | @alpha-researcher | @crypto-data-engineer | Funding rate data needed |
| `GRADE_PENDING_NOW` | any | @crypto-strategy-tuner | Force-grade specific strategy |

---

## Agent Shared Infrastructure

All agents read/write to `.gemini/shared/` for cross-agent coordination:

| File | Purpose |
|---|---|
| `KNOWLEDGE_BASE.md` | Auto-regenerated master snapshot of all 157 strategies (grades, metrics, params). Rebuilt by @crypto-fullstack on every finalize cycle |
| `AGENT_COLLABORATION.md` | Running log of cross-agent actions, handoffs, and decisions |
| `SYSTEM_CHANGELOG.md` | Timestamped record of every file change made by any agent |
| `GLOBAL_LTM.md` | Global long-term memory — patterns and constraints that all agents share |
| `AGENT_COLLAGRAM.md` | Visual diagram of agent collaboration flows |

Each agent also maintains its own:

| File | Purpose |
|---|---|
| `session_memory.md` | Last N session summaries (what was done, what changed) |
| `LTM.md` | Agent-specific long-term memory (what works, what to avoid) |
| `inbox/active/` | Incoming messages (unprocessed) |
| `inbox/dead_letter/` | Processed messages (archived) |
| `heartbeat.json` | Live status shown on Phase 6 dashboard (ONLINE / IDLE / RUNNING) |

---

## Strategy Development Lifecycle

Full journey from idea → production-ready strategy:

```
[1] DISCOVERY (@alpha-researcher)
    Web search → raw alpha idea
    ↓
[2] CANDIDATE CARD (@alpha-researcher)
    Mathematical formulation → YAML card in factor_library/
    Poison Filter + Library Guard + Data Universe Guard
    ↓ inbox: NEW_FACTOR_DISCOVERED
[3] BUILD (@alpha-developer)
    Python strategy class → Logic Switches → Regime Guards
    AST check → Signal Sanity → Smoke test
    ↓
[4] REGISTER + OPTIMIZE (@alpha-developer + scripts)
    Register in settings.py → Optuna finetune (100+ trials)
    → Update settings.py with best params
    ↓
[5] STABILITY CHECK (@alpha-developer)
    WFO 4-window test → PBO audit (< 0.40)
    Pass → VALIDATED | Fail → AUTOPSY → REJECTED (entry kept)
    ↓
[6] GRADE (@crypto-strategy-tuner)
    scan_all.py → classify_strategies.py
    GOOD / MEDIOCRE / BAD → scan_results.json
    ↓
[7] ELITE REPORT (GOOD only, @crypto-strategy-tuner)
    Recent regime check → correlation warning → deployment recommendation
    → elite_report/ Market Fit Memo
    ↓
[8] LIVE PAPER TRADING (planned)
    @crypto-pattern-agent consumes wisdom_matrix.csv + elite_report/
```

---

## Strategy Library

**157 registered strategies** across 5 coins × 5 timeframes.

**Strategy classes (30+):**
EMA Crossover · RSI Mean Reversion · VWAP ATR Reversion · Supertrend Pro · Liquidity Sweep Reversal · Order Block SMC · ICT Holy Trinity · WaveTrend MFI Divergence · Lorentzian Classification · Z-Score Stat Arb · Fisher Transform · Keltner RSI Reversion · Aroon RSI · EMA Ribbon RSI · Envelope Mean Reversion · Choppiness Keltner Breakout · Dynamic Swing VWAP · ForgeStrategy (AI-composed) · and 15+ more

**Shared Math Library** (`strategy_backtest/library.py`) — importable factors used by all strategies:
`calc_atr` · `calc_ema` · `calc_rsi` · `calc_macd` · `calc_adx_dmi` · `calc_bollinger_bands` · `calc_zscore` · `calc_vwap` · `calc_supertrend` · `calc_ichimoku` · `calc_keltner_channels` · `calc_stoch_kdj` · `calc_wavetrend` · `calc_mfi` · `calc_fisher_transform` · `calc_vrsi` · `detect_fvg` · `detect_order_blocks` · `detect_divergence` · and more

**settings.py Write Guards** (prevents agent corruption):
- Any write to `settings.py` checks: new ID count ≥ old ID count (abort if IDs would be dropped)
- Last 5 timestamped snapshots saved to `strategy_backtest/.settings_snapshots/`

---

## Main Controller — Flask Dashboard

**Start:** `bash start_server.sh` → `http://localhost:5001`

**Key API Routes:**
```
GET  /api/strategies                          → full strategy list with grades
POST /api/run_backtest                        → run backtest for a strategy ID
GET  /api/validate_strategy?strategy_id=X    → 26-rule deep validation
GET  /api/scan_summary                        → live GOOD/MEDIOCRE/BAD counts
POST /api/force_rescan                        → trigger full rescan of all strategies
GET  /api/wfo_results?strategy_id=X          → walk-forward results
POST /api/finetune                            → trigger Optuna fine-tune
```

**Key files:** `main_controller/main.py`

---

## Project Structure

```
Crypto-RL/
├── main_controller/              # Flask API server (port 5001)
├── strategy_backtest/
│   ├── settings.py               # 157-strategy registry (all configs + params)
│   ├── strategies/               # Individual strategy class implementations
│   ├── library.py                # Shared math factors (RSI, VWAP, ATR, etc.)
│   ├── engine.py                 # Backtest execution engine
│   ├── validator.py              # 26-rule deep validation engine
│   └── .settings_snapshots/      # Timestamped settings.py backups (write guard)
├── strategy_forge/
│   ├── signals/
│   │   ├── entry_signals.py      # Entry signal implementations
│   │   ├── filter_signals.py     # Filter signal implementations
│   │   └── exit_signals.py       # Exit method implementations
│   └── composer/                 # DNA composer + genetic evolution
├── phase_0/                      # Data collection scripts
├── phase_1/                      # DRL training + Optuna optimization
├── phase_2/                      # Statistical validation dashboard
├── phase_4/                      # Backtest + deep validation dashboard
├── phase_5/                      # PBO analysis
├── phase_6_agent_monitor/        # Strategy scan/grade + Alpha Forge v2 vault
│   └── alpha_forge_v2/
│       ├── hypho_report/         # Hypothesis reports (pre-build)
│       ├── dev_report/           # Development reports (post-build)
│       ├── backtest_report/      # Scan/grade reports (all strategies)
│       ├── autopsy_report/       # Post-mortems (rejected strategies)
│       └── elite_report/         # Market fit memos (GOOD strategies)
├── phase_7/                      # Recursive pattern mining + wisdom matrix
├── phase_9_flow/                 # Agentic pipeline flow visualiser
├── phase_10/                     # Pairs trading (cointegration Z-score)
├── phase_11/                     # Anti-correlation crossover (momentum rotation)
├── phase_12/                     # Strategy Forge dashboard
├── .gemini/
│   ├── skills/                   # 6 agent skill definitions + inboxes + session memory
│   │   ├── alpha-researcher/
│   │   ├── alpha-developer/
│   │   ├── crypto-strategy-tuner/
│   │   ├── crypto-fullstack/
│   │   ├── crypto-data-engineer/
│   │   └── crypto-qa-tester/
│   └── shared/                   # Cross-agent shared files (KNOWLEDGE_BASE, LTM, logs)
├── Crypto_Agent/
│   └── agent_watcher.py          # Agent launcher + inbox poller + scheduler
├── core/                         # ElegantRL DRL engine + trading environments
├── factor_library/               # Alpha candidate cards (Markdown, by category)
├── docs/                         # Documentation
└── requirements.txt              # Python dependencies
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| DRL Training | PyTorch · ElegantRL (local copy) · SAC · PPO · TD3 · DDPG · A2C |
| Hyperparameter Search | Optuna (Bayesian TPE sampler) |
| Technical Indicators | TA-Lib (C-backed) + custom library.py |
| Statistical Validation | scipy · statsmodels · t-test · CPCV · PBO |
| Data | Binance API · CCXT · pandas · Parquet |
| Web Dashboard | Flask · Vanilla JS · Canvas API (charts) |
| AI Agents | Google Gemini 2.5 Flash / 3.1 Pro Preview via `agy` CLI |
| Strategy Fine-Tuning | Optuna per-strategy (100–200 trials) |
| Agent Orchestration | `agent_watcher.py` (inbox polling + scheduled tasks) |

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add API keys (never commit these)
cp .env.example .env        # fill in BINANCE_API_KEY, BINANCE_SECRET

# 4. Start the dashboard
bash start_server.sh        # → http://localhost:5001

# 5. (Optional) Start an AI agent
python Crypto_Agent/agent_watcher.py tuner
```

---

## Security

- `.env`, `binance_api.txt`, `open_router_API.txt`, `reddit_api.txt` — **all git-ignored, never committed**
- `dataset/` (6.5 GB), `train_results/` (11 GB), `venv/` — git-ignored
- `settings.py` is write-guarded — any agent script that modifies it checks for ID drops before writing and keeps 5 timestamped snapshots
