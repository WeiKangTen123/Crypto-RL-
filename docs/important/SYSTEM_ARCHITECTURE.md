# Crypto-RL — Full System Architecture

> Last updated: 2026-06-26 (session 7)
> Covers: Master dashboard shell, DRL pipeline (Phase 0–5), Agentic research pipeline (Phase 6), Pattern mining (Phase 7), FreqAI layer, and all inter-component linkages.
> Evidence-verified: all linkages confirmed by reading actual code, not just file names.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Master Dashboard — How the UI Fits Together](#2-master-dashboard--how-the-ui-fits-together)
3. [Full Phase Pipeline](#3-full-phase-pipeline)
4. [The 6 Agents — Roles & Stages](#4-the-6-agents--roles--stages)
5. [Inter-Agent Communication](#5-inter-agent-communication)
6. [File Linkage Map](#6-file-linkage-map)
7. [Phase 7 — Pattern Mining & Wisdom Matrix](#7-phase-7--pattern-mining--wisdom-matrix)
8. [FreqAI Layer](#8-freqai-layer)
9. [Data Infrastructure](#9-data-infrastructure)
10. [Agent Memory System](#10-agent-memory-system)
11. [Known Gaps & Status](#11-known-gaps--status)
12. [Entry Points — How to Start Everything](#12-entry-points--how-to-start-everything)

---

## 1. System Overview

Crypto-RL is a **multi-layer autonomous trading system** built on three parallel tracks:

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRACK A — DRL TRAINING (Phases 0–5)                                │
│  Deep Reinforcement Learning model trained with CPCV cross-         │
│  validation, Optuna hyperparameter search, and PBO overfit check.   │
│  Output: actor.pth — a neural net that can trade live.              │
└─────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TRACK B — AGENTIC RESEARCH PIPELINE (Phase 6)                      │
│  6 autonomous Gemini agents that discover alpha, build rule-based   │
│  strategies, tune them with Optuna, and watch each other via a      │
│  real-time dashboard.                                               │
│  Output: settings.py — registry of graded rule-based strategies.   │
└─────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TRACK C — PATTERN MINING (Phase 7)                                 │
│  Mines every GOOD strategy across Micro / Meso / Macro time         │
│  windows, classifies market regimes, stores best params per regime. │
│  Output: wisdom_matrix.csv — regime-aware parameter lookup table.  │
└─────────────────────────────────────────────────────────────────────┘
```

**Core frameworks:**

| Framework | Role |
|---|---|
| ElegantRL (local copy in `core/train/`) | DRL training engine — SAC, PPO, TD3, DDPG, A2C |
| Optuna | Bayesian hyperparameter search (Phase 1 + `finetune.py`) |
| CCXT / python-binance | Exchange connector (live/paper data + Binance OHLCV) |
| TA-Lib | C-based technical indicators (RSI, ATR, BB, EMA…) |
| Flask | Web server for master dashboard + all API routes (port **5001**) |
| FreqAI / Freqtrade | Secondary ML trading framework (standalone, `freqai/`) |

---

## 2. Master Dashboard — How the UI Fits Together

The `main_controller/` is the **master navigation shell** — a single entry point that loads every phase dashboard inside an iframe. Each phase folder has its own self-contained `index.html` so it can be developed and viewed independently.

```
Browser → http://127.0.0.1:5001
         │
         └── main_controller/index.html  (nav sidebar + iframe container)
                  │
                  ├── [Pipeline Overview]  → renders inline
                  │     Shows pipeline_state.json cards (Phase 0–5 status)
                  │     Agent heartbeat summary + AGENT_COLLABORATION.md log
                  │
                  ├── [Phase 0: Data]      → renders inline
                  │     Parquet data cards, dataset preview (Plotly chart)
                  │     Reads: /datasets  /processed  /data_preview
                  │
                  ├── [Phase 2: Validate]  → iframe ──▶ phase_2/validation_dashboard/dashboard.html
                  │
                  ├── [Phase 4: Backtest]  → iframe ──▶ phase_4/dashboard/index.html
                  │
                  ├── [Phase 5: PBO]       → iframe ──▶ phase_5/dashboard/index.html
                  │
                  ├── [Phase 6: Agent Monitor] → iframe ──▶ /agent_monitor (Flask route)
                  │                                          serves phase_6_agent_monitor/
                  │
                  └── [Phase 7: Pattern Discovery] → iframe ──▶ phase_7/dashboard/index.html
```

**Why every folder has its own `index.html`:** each sub-dashboard is independently runnable. The master shell just composes them together — you can open `phase_4/dashboard/index.html` directly in a browser to inspect backtest charts without starting Flask.

**Flask API endpoints used by the master shell:**

| Endpoint | Used by |
|---|---|
| `GET /check_updates` | Polls `pipeline_state.json` every 2s for phase card status |
| `GET /list_results` | Returns available `train_results/` folders for Phase 2/4/5 selectors |
| `GET /datasets` | Returns parquet file list for Phase 0 data cards |
| `GET /processed` | Returns processed pickle datasets (trainval + trade) |
| `GET /data_preview` | Returns OHLCV close prices for Plotly chart preview |
| `POST /run/{phase}` | Triggers a phase script subprocess |
| `POST /stop/{phase}` | Kills a running phase subprocess |
| `GET /api/agent_console` | Returns heartbeats + AGENT_COLLABORATION.md + health log |
| `GET /agent_monitor` | Serves `phase_6_agent_monitor/index.html` |

---

## 3. Full Phase Pipeline

```
╔══════════════════════════════════════════════════════════════╗
║  PHASE 0 — DATA COLLECTION                                   ║
╠══════════════════════════════════════════════════════════════╣
║  Scripts: phase_0/dl_macro_data.py                           ║
║           phase_0/dl_trainval_data.py                        ║
║           phase_0/dl_trade_data.py                           ║
║  Downloads 7+ years of 4h OHLCV for BTC + 5 feature tickers  ║
║  (ETH, DXY, SPY, VIX, JPY).                                   ║
║  Computes 30 features per timestamp:                          ║
║    • 14 per-ticker (close, volume, rsi, dx, ultosc, obv, atr, ║
║      bband_width, ema_ratio, log_return + OHLCV)              ║
║    • 15 cross-asset (price/volume ratios + 20-bar corr        ║
║      vs ETH / DXY / SPY / VIX / JPY)                         ║
║    • 1 VIX panic signal (vix_log_return)                      ║
║  Output: price_array.pkl + tech_array.pkl + time_array.pkl    ║
║  Status: phase_0_macro ✓  phase_0_trainval ✓  phase_0_trade ✓║
╚══════════════════════════╦═══════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 1 — HYPERPARAMETER OPTIMISATION                       ║
╠══════════════════════════════════════════════════════════════╣
║  Scripts: core/optimize_wf.py / optimize_kcv.py /            ║
║           optimize_cpcv.py (most rigorous)                   ║
║  Runs Optuna (50 trials). Each trial:                        ║
║    1. Samples hyperparams                                     ║
║    2. Trains DRL agent on train split (ElegantRL)            ║
║    3. Evaluates on validation split                          ║
║    4. Reports Sharpe ratio as objective                      ║
║  CV modes: Walk-Forward | K-Fold (5 splits) | CPCV           ║
║  Output: train_results/{name}/best_trial + actor.pth         ║
║  Status: PENDING                                             ║
╚══════════════════════════╦═══════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 2 — STATISTICAL VALIDATION                            ║
╠══════════════════════════════════════════════════════════════╣
║  Script: phase_2/validate.py                                 ║
║  Mean Sharpe ± 95% CI, t-test vs Buy-and-Hold               ║
║  Output: phase_2/validation_dashboard/dashboard.html         ║
║  Status: completed (2026-05-26)                              ║
╚══════════════════════════╦═══════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 4 — BACKTEST (unseen data 2024–2026)                  ║
╠══════════════════════════════════════════════════════════════╣
║  Script: phase_4/backtest.py                                 ║
║  Loads actor.pth + best_trial, runs on trade data via        ║
║  CryptoEnvCCXT inference loop.                               ║
║  Metrics: Sharpe, Sortino, MDD, Win Rate, Return vs HODL     ║
║  Output: phase_4/dashboard/data.js + index.html              ║
║  Status: Fixed 2026-06-14 (pickle regenerated, float64 cast) ║
╚══════════════════════════╦═══════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 5 — PBO (Probability of Backtest Overfitting)         ║
╠══════════════════════════════════════════════════════════════╣
║  Script: phase_5/pbo.py                                      ║
║  CPCV framework (López de Prado & Bailey).                   ║
║  Threshold: PBO < 0.5 = genuine edge. PBO > 0.5 = overfit.  ║
║  Output: phase_5/dashboard/ (pbo_data.js + index.html)       ║
║  Status: completed (2026-05-22)                              ║
╚══════════════════════════╦═══════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 6 — AGENTIC RESEARCH PIPELINE (see Section 4)         ║
╠══════════════════════════════════════════════════════════════╣
║  6 autonomous Gemini agents run in parallel.                 ║
║  Researcher → Developer → Tuner → GOOD strategies            ║
║  Monitored via phase_6_agent_monitor/ dashboard.             ║
║  Output: settings.py with 119 graded strategies              ║
╚══════════════════════════╦═══════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════╗
║  PHASE 7 — RECURSIVE PATTERN MINING (see Section 7)          ║
╠══════════════════════════════════════════════════════════════╣
║  Script: phase_7/miner.py                                    ║
║  Mines GOOD strategies across Micro/Meso/Macro windows.      ║
║  Output: phase_7/data/wisdom_matrix.csv                      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 4. The 6 Agents — Roles & Stages

All agents are autonomous Gemini processes launched by `Crypto_Agent/agent_watcher.py`. Each polls its own inbox every 30 seconds and updates `heartbeat.json` every 15 seconds via a background thread.

**Model cascade on quota exhaustion:** each agent starts at its assigned tier and falls back to the next on quota exhaustion.

```
Tier 0: gemini-3.1-pro-preview       ← Researcher default
Tier 1: gemini-2.5-flash             ← Fullstack / Developer / Tuner default
Tier 2: gemini-3.1-flash-lite-preview← Data Engineer default
Tier 3: gemini-2.5-flash-lite        ← QA default

On quota hit: Pro → Flash → Flash-Lite-Preview → Flash-Lite
```

Researcher on Flash (fallback): queue check only, no web search pipeline. Full web pipeline requires Pro.

---

### @alpha-researcher — Discovery Agent

**Schedule:** Every 6 hours | **Entry:** `agent_watcher.py researcher`

| Stage | Action | Output |
|---|---|---|
| [1/3] WEB_SEARCH | Hunt Tier 1 (GitHub, TradingView) → Tier 2 (arXiv, SSRN). Tier 3 (Reddit) is optional. Uses **gemini-3.1-pro-preview**. | — |
| [2/3] EXTRACT_ALPHA | Model math, apply Guards, write Candidate Card. Uses **gemini-2.5-flash**. | `factor_library/{CATEGORY}/{date}_{name}.md` |
| [3/3] HYPHO_REPORT_&_INDEX_SYNC | Write formal hypothesis report, sync Obsidian, send inbox message to Developer. Uses **gemini-2.5-flash**. (Skipped if no novel factor). | `hypho_report/*.md` & `alpha-developer/inbox/*.json` |

**Queue check (Flash model):** Scans `factor_library/` for Candidate Cards with `status: QUEUED`. Implements top 1–2 if model available, otherwise logs idle.

**Institutional Guards:**
- **Poison Filter** — never reuse a concept in `autopsy_report/` without explicit fix
- **Library Guard** — never re-implement RSI/VWAP/ATR; reference `library.py`
- **Data Universe Guard** — `coins:` must only be from: `BTC`, `ETH`, `BNB`, `SOL`, `XRP`. `timeframes:` must only be from: `5m`, `15m`, `1h`, `4h`, `1d`. `known_data_gaps.md` logs partial gaps within datasets — it is NOT a blocklist; all 5 coins are usable across all 5 timeframes. `30m` exists but is unused — avoid. No other coins or intervals exist in the dataset.

---

### @alpha-developer — Strategy Builder

**Schedule:** Every 360 min | **Entry:** `agent_watcher.py developer`

| Stage | Action | Output |
|---|---|---|
| [1/7] INGEST | Read Candidate Card, extract `coins`/`timeframes`/`Minimum history` from YAML, map library.py functions | — |
| [2/7] BUILD | Check library.py + existing strategies first. Write `strategies/{name}.py` with Logic Switches, `SIGNAL_PARAMS`, inline regime masks (no `check_regime()` method). | `strategy_backtest/strategies/{name}.py` |
| [3/7] SYNTAX | Python AST validation (Flash) | — |
| [4/7] SMOKE | Signal count check first (zero signals = impossible condition), then 1-day backtest, verify `manage_trade` action strings (Flash) | — |
| [5/7] DEV_REPORT | 1) Baseline on card's primary coin/tf. 2) Register in settings.py with defaults. 3) Run `finetune.py` (Optuna). 4) Final backtest with finetuned params. 5) Cross-asset same tf. 6) Dev report with finetuned metrics. | `alpha_forge_v2/dev_report/{date}_{id}_{name}_dev.md` + `settings.py` |
| [6/7] WFO_EVO | 4-window Walk-Forward stability check on **optimized** params | — |
| [7/7] PBO_AUDIT_&_MANIFEST | Overfit check (threshold 0.40). Verify settings.py already has Optuna best params from Stage 5 (do NOT overwrite with WFO params). Sync Obsidian, notify Fullstack. (Flash) | `autopsy_report/` on fail |
| [!] ON_FAIL | **Any stage crash** (TA_BAD_PARAM, import error, unfixable zero-trade): write autopsy, set card `status: REJECTED`, notify Tuner | `autopsy_report/{date}_{id}_{name}_autopsy.md` |

**Critical Stage 5 rule:** Registration in `settings.py` is MANDATORY at Stage 5 with default params, then immediately updated with Optuna best via `finetune.py`. Even if WFO/PBO later rejects the strategy, the entry stays in settings.py with best-found params so the tuner can rescan and salvage later.

**Stage 5 coin/tf rule:** Primary coin = first in card's `coins` YAML. Primary tf = first in card's `timeframes` YAML. Cross-asset checks use the same tf on the other listed coins. `date_to` always `2026-05-31`. `date_from` by tf: `5m→2025-05-31` | `15m→2024-05-31` | `1h/4h→2023-05-31` | `1d→2022-05-31`.

**WFO does NOT produce best params:** WFO tests stability across windows, not param search. `settings.py` params come from `finetune.py` at Stage 5 and are not overwritten at Stage 8.

**BaseStrategy contract (developer must know):**
- `super().__init__(df, **kwargs)` auto-assigns all kwargs via `setattr` — only explicitly assign params needing type-casting
- `SIGNAL_PARAMS = frozenset({...})` — which params affect signal generation (vs risk-only)
- `validate_params(cls, params)` — override to skip invalid optimizer combos
- `generate_signals()` must set `self.df = df` before returning
- No `check_regime()` in BaseStrategy — implement regime guards as inline boolean mask columns inside `generate_signals()`

**After Stage 8:** Developer appends an **Implementation Metadata Block** back to the original Candidate Card in `factor_library/` (defined in `references/templates.md`) — this closes the loop.

**Optimization tools available to Developer:**
- `.gemini/skills/crypto-strategy-tuner/scripts/finetune.py` — Optuna (100+ trials, multi-objective); called at Stage 5 before WFO. Auto-updates `settings.py` + strategy `__init__` defaults with best params. Scoring: Sharpe(55%) + Recovery Factor(20%) + Profit Factor(15%) + return bonus; hard guards: MDD > 70% and min-trades (30 if ≤365-day period, 60 otherwise). Baseline Sharpe is re-computed from current params on each run — not read from stale scan_results.json.
- `strategy_backtest/scripts/wfo_runner.py` — 8-fold anchored expanding-window walk-forward framework (dev tool, not called automatically). Computes WF efficiency, IS→OOS decay, OOS/IS MDD ratio, and fold-level Sharpe. PASS thresholds: WF efficiency ≥ 0.5, MDD ratio ≤ 1.5, decay ≤ 0.5.
- `strategy_backtest/validator.py` — full 26-rule Rulebook validator. Runs T0 data integrity → T1 fatal gates (Sharpe, MDD, WFO, lookahead probe, regime survival) → T2 quality gates (PBO, DSR, random-label, GTP) → T3 warnings (bootstrap, sensitivity, truncation) → Crypto Pack (funding, news, vol-regime). Scores out of 100; verdict APPROVED if ≥ 70%.

---

### @crypto-strategy-tuner — Optimizer & Grader

**Schedule:** Every 120 min | **Entry:** `agent_watcher.py tuner`
**Scripts:** `scripts/scan_all.py` · `scripts/finetune.py` · `scripts/classify_strategies.py` · `scripts/find_worst_strategy.py`

| Stage | Action | Output |
|---|---|---|
| [1/4] AUDIT | Load `scan_results.json`, run `classify_strategies.py` to grade any PENDING entries | — |
| [2/4] WORK_CYCLE | Run `scan_all.py` (full sweep) + `finetune.py` (Optuna 150 trials on worst BAD strategy). Limit: 1 autonomous fine-tune per wake-up | `scan_results.json` updated |
| [3/4] REPORTING | Write backtest report per strategy | `alpha_forge_v2/backtest_report/{id}_{name}_backtest.md` |
| [4/4] MANIFEST | On GOOD: write elite memo, sync Obsidian, notify Researcher via inbox | `alpha_forge_v2/elite_report/{id}_{name}_elite.md` |
| [!] ON_ERROR | Any ERROR strategy during scan: write autopsy, send `FACTOR_FAILURE_REPORT` to Researcher inbox | `autopsy_report/{date}_{id}_{class}_autopsy.md` |

**Grading thresholds (confirmed from `classify_strategies.py` line 58):**

| Grade | Sharpe | Meaning |
|---|---|---|
| GOOD | ≥ 1.0 | Ready for paper trading |
| MEDIOCRE | 0.3 – 1.0 | Worth tuning |
| BAD | < 0.3 | No meaningful edge |

**Auto-expand (finetune.py):** If best param hits ceiling/floor (within 0.5% of range span), expands range by 50% and re-runs at 75 trials.

**Proactive tuning:** Uses `find_worst_strategy.py` to find the lowest-Sharpe BAD strategy not tuned in the last 24h, then runs `finetune.py` on it autonomously.

---

### @crypto-data-engineer — Data Guardian

**Schedule:** Every 360 min | **Entry:** `agent_watcher.py data`

| Stage | Action | Output |
|---|---|---|
| [1/4] SCAN | Run `scripts/health_scout_v2.py --once` — scans all parquets for gaps/dtype errors | `logs/system_health.log` |
| [2/4] ANALYZE | Identify gap patterns, schema errors per `references/data_specs.md` rules | — |
| [3/4] REPAIR | Run `scripts/incremental_fetcher.py` (new bars only) or `scripts/repair_dtypes.py` (dtype fix). VPN required — connect via `scripts/vpn_manager.py` first | Repaired parquets + `.bak` snapshots |
| [4/4] VERIFY | Publish gap state | `known_data_gaps.md` |

**Full script inventory:**

| Script | Purpose |
|---|---|
| `health_scout_v2.py` | Integrity scan — gaps, dtype errors, freshness |
| `incremental_fetcher.py` | Fetches only new bars since last timestamp (not full re-download) |
| `repair_dtypes.py` | Fixes object/string dtype columns back to float64 |
| `funding_rate_fetcher.py` | Downloads `funding_rate.parquet` for all 5 coins at 4h |
| `vpn_manager.py` | ProtonVPN automation — **must connect before any Binance fetch** |
| `check_cols.py` | Quick column presence validation |
| `sync_all.py` | VPN-aware full parquet sync orchestrator |

**Data scope:** BTC, ETH, BNB, SOL, XRP × 1m, 5m, 15m (BTC/ETH only), 30m, 1h, 4h, 1d
**Macro folders (DXY, JPY, SPY, VIX):** used only for DRL training — Data Engineer does NOT scan or repair these.

**Gap tolerance rules (from `data_specs.md`):**

| Missing bars | Action |
|---|---|
| ≤ 3 in a day | INFO only |
| 4–20 in a day | WARN — log, no inbox |
| > 20 in a single day | STALE — escalate to `@crypto-fullstack` |
| Full day missing | STALE_CRITICAL — HIGH inbox to `@crypto-fullstack` immediately |

---

### @crypto-qa-tester — Test Orchestrator

**Schedule:** Every 720 min | **Entry:** `agent_watcher.py qa`
**Script:** `scripts/system_test.py --once` — writes results to `logs/qa_results.log`

| Stage | Action | Routes failures to |
|---|---|---|
| [1/5] GROUP_1 | Validate Flask API routes | @crypto-fullstack |
| [2/5] GROUP_2 | Verify strategy imports + engine integrity | @alpha-developer |
| [3/5] GROUP_3 | Audit data linkage + backtest smoke | @crypto-data-engineer |
| [4/5] GROUP_5 | Registration audit: unregistered classes + settings/scan_results ID sync | @alpha-developer / @crypto-strategy-tuner |
| [5/5] FINALIZE | Route unhandled failures, append to AGENT_COLLABORATION.md | — |

**Protocol:** Retry failed tests once before escalating. Second consecutive failure = escalate with note "confirmed on 2 consecutive runs".

**Standalone scripts (not part of automated suite):**
- `scripts/test_date.py` / `scripts/test_date_repro.py` — unit tests for `_safe_date()` edge cases; used by developers, not called by `system_test.py`.

---

### @crypto-fullstack — Infrastructure Engineer

**Schedule:** Every 720 min | **Entry:** `agent_watcher.py fullstack`

| Stage | Action | Output |
|---|---|---|
| [1/4] TRIAGE | Read `main_controller/server.log` + `.gemini/logs/error_log.jsonl`. **Read `references/bug_patterns.md` first** for known root causes before debugging | — |
| [2/4] IMPLEMENT | Patch `main.py` / `monitor_app.js` / `index.html` / CSS. Always `.bak` before edit | Fixed files |
| [3/4] CHAOS_TEST | Run `scripts/chaos_test.py` — sweeps all Flask routes | — |
| [4/4] FINALIZE | Update `main_controller/agent_status.json`, sync `pipeline_state.json`, run `sync_knowledge_base.py`, notify agents | `KNOWLEDGE_BASE.md` regenerated |

**Error log system:**
- `.gemini/logs/error_log.jsonl` — all agent runtime errors (central store)
- `.gemini/logs/last_processed_ts.txt` — tracks what Fullstack already acted on (prevents re-processing old errors on every 30-min wake-up)
- `.gemini/logs_archive/*.gz` — rotated compressed health logs (by `shared/log_rotator.py`)

**Toolbox:**
- `scripts/chaos_test.py` — Flask API route sweep (run after every backend change)
- `scripts/zombie_sweep.py` — reads `Crypto_Agent/active_watchers.json`, clears dead PIDs
- `scripts/sync_knowledge_base.py` — auto-regenerates `KNOWLEDGE_BASE.md` from `scan_results.json` + `settings.py`; run at every [4/4] FINALIZE
- `references/bug_patterns.md` — known error routing table (Flask errors, agent tooling errors, JS bugs)
- `main_controller/GEMINI.md` — sub-directory protocol for this folder

---

## 5. Inter-Agent Communication

### Message Flow

```
  @alpha-researcher
       │  NEW_FACTOR_DISCOVERED
       ▼
  @alpha-developer
       │  STRATEGY_READY
       ▼
  @crypto-strategy-tuner ──FINETUNE_PROMOTED──▶ @alpha-researcher
       │  STRATEGY_VALIDATED
       ▼
  @crypto-fullstack

  @crypto-data-engineer ──DATA_GAP──────────────▶ @alpha-researcher
  @crypto-data-engineer ──DATA_REPAIRED──────────▶ @alpha-researcher

  Dashboard ──GRADE_PENDING_NOW──────────────────▶ @crypto-strategy-tuner
  Dashboard ──RUN_SCAN_NOW / FORCE_RESCAN_NOW────▶ @crypto-strategy-tuner

  @crypto-qa-tester ──routes by failure type────▶ correct agent
```

### Inbox Architecture

```
.gemini/skills/{agent}/inbox/
  ├── {ts}_from_{source}_{topic}.json   ← active messages (max 5 processed per run)
  ├── active/                           ← currently being processed
  └── dead_letter/                      ← TTL expired (48h) or stuck > 30 min
```

Resolved messages archived to `.gemini/shared/resolved_inbox.jsonl` (append-only, 141KB+).

### Agent Heartbeat

**File:** `.gemini/skills/{agent}/heartbeat.json`

```json
{
  "ts": "2026-06-14T10:00:00",
  "status": "ONLINE | STANDBY | OFFLINE | ERROR",
  "action": "[X/Y] STAGE_NAME: Details",
  "model": "gemini-model-id",
  "last_action": "Previous action text"
}
```

The `[X/Y]` prefix in `action` drives the stepper infographic in the Phase 6 dashboard.

---

## 6. File Linkage Map

```
factor_library/{CATEGORY}/
  └── {date}_{name}.md               ←── Researcher writes Candidate Cards
        │  (YAML frontmatter: status, sharpe, coins, timeframes, etc.)
        │  After Stage 8: Developer appends Implementation Metadata Block
        ▼
strategy_backtest/
  ├── library.py                     ←── SHARED math factors (RSI, VWAP, ATR, squeeze…)
  │        ↑  imported by all strategies + verified by Library Guard
  ├── strategies/{name}.py           ←── Developer writes here (Stage 2)
  ├── settings.py                    ←── SINGLE SOURCE OF TRUTH (119 strategies)
  │        ↑  read by: Tuner (scan/finetune), Phase 7 (miner.py), QA, Phase 4
  │        ↑  written by: Developer (Stage 5, mandatory) + Tuner (param updates)
  ├── engine.py                      ←── Backtest simulator (slippage, margin, P&L)
  ├── run_backtest.py                ←── CLI runner used by all agents + Phase 7
  ├── metrics.py                     ←── Sharpe, MDD, Win Rate, PF + DSR p-value,
  │                                        Cost Ratio, Worst Daily Loss, Monthly GTP,
  │                                        Weekend/Weekday Sharpe, Regime MDD
  ├── validator.py                   ←── 26-Rule Rulebook validator (T0→T1→T2→T3→CR)
  │        usage: python strategy_backtest/validator.py --strategy 3 [--quick] [--save]
  ├── risk.py                        ←── Position sizing, leverage, slippage
  ├── base_strategy.py               ←── BaseStrategy class (all strategies inherit)
  ├── optimizer/
  │   ├── optimizer.py               ←── Parallel grid-search (multiprocessing pool)
  │   ├── optimize_{name}.py         ←── ~35 strategy-specific grid scripts
  │   └── optimize_{name}/results.csv←── Grid search outputs
  └── scripts/
      ├── wfo_runner.py              ←── 8-fold anchored expanding-window WFO framework
      │                                   computes: WF efficiency (T2-01), IS→OOS decay
      │                                   (T2-02), OOS/IS MDD ratio (T1-08), per-fold Sharpe
      │                                   usage: python ...wfo_runner.py --strategy 3 [--folds 8]
      ├── wfo_liquidity_sweep.py     ←── Strategy-specific WFO sweep
      └── tip_breakout_sweep.py      ←── TIP breakout parameter sweep

dataset/{coin}/{tf}/
  ├── spot_ohlcv.parquet             ←── OHLCV + taker flow (Data Engineer maintains)
  └── funding_rate.parquet           ←── 4h only, all 5 coins (funding_rate_fetcher.py)
       read by: engine.py, Phase 0/4/7, funding-rate strategies

phase_6_agent_monitor/
  ├── index.html / monitor_app.js    ←── Phase 6 Agent Monitor SPA
  ├── monitor_styles.css
  └── alpha_forge_v2/
      ├── hypho_report/              ←── Stage 01: Researcher output
      ├── dev_report/                ←── Stage 02: Developer Stage 5 output
      ├── backtest_report/           ←── Stage 03: Tuner Stage 3 output
      ├── elite_report/              ←── Stage 04: Tuner Stage 4 (GOOD only)
      └── autopsy_report/            ←── Failure docs (Developer any-stage crash + Tuner ERROR grade)

phase_7/
  ├── miner.py                       ←── Entry point: reads settings.py + engine.py
  ├── scripts/
  │   ├── regime_classifier.py       ←── Labels each window: TREND_UP, CHOP_VOL…
  │   ├── window_generator.py        ←── Splits history into Micro/Meso/Macro windows
  │   ├── window_tuner.py            ←── Optuna search within each window
  │   └── patch_metrics.py           ←── Metrics helpers
  └── data/
      ├── wisdom_matrix.csv          ←── OUTPUT: regime-aware param lookup table
      └── raw_results/               ←── Per-window JSON cache (skip if exists)

.gemini/skills/{agent}/
  ├── inbox/                         ←── Message queue
  ├── heartbeat.json                 ←── Live status ([X/Y] stage)
  ├── activity.log                   ←── Timestamped action log
  ├── session_memory.md              ←── Short-term memory template / seed
  ├── session_memory                 ←── Live runtime file agents actually write to (no extension)
  ├── LTM.md                         ←── Long-term wisdom (permanent)
  ├── SKILL.md                       ←── Full agent instructions
  ├── STAGES.md                      ←── Quick-reference stage guide (alpha-researcher + alpha-developer only)
  ├── references/                    ←── Agent-specific reference docs
  └── scripts/                       ←── Agent-specific executable scripts

.gemini/shared/
  ├── resolved_inbox.jsonl           ←── All-time message archive (append-only)
  ├── GLOBAL_LTM.md                  ←── System-wide wisdom
  ├── KNOWLEDGE_BASE.md              ←── Strategy master table (LIVE/PAPER/BENCH status)
  ├── AGENT_COLLABORATION.md         ←── Cross-agent handoff log
  ├── SYSTEM_CHANGELOG.md            ←── File-level change history
  ├── research_results/              ←── Legacy: Researcher saved JSON outputs (not active)
  └── logger.py / memory_manager.py / log_rotator.py

.gemini/logs/
  ├── error_log.jsonl                ←── All agent runtime errors (central store)
  └── last_processed_ts.txt          ←── Fullstack's "already seen up to here" marker

.gemini/logs_archive/
  └── system_health.log.*.gz         ←── Rotated compressed health logs

main_controller/
  ├── main.py                        ←── Flask server (port 5001, all API routes)
  ├── index.html / app.js / styles.css←── Master dashboard shell
  ├── pipeline_state.json            ←── Phase run status + metadata
  ├── agent_status.json              ←── Fullstack self-reported status
  ├── server.log                     ←── Flask error trail
  ├── phase_X.log                    ←── Per-phase execution logs
  ├── GEMINI.md                      ←── Sub-directory protocol for fullstack agent
  └── heartbeat.json                 ←── Fullstack heartbeat (mirrors skill folder)

Crypto_Agent/
  ├── agent_watcher.py               ←── DAEMON: polls inbox, spawns Gemini, heartbeats
  └── active_watchers.json           ←── PID registry (prevents duplicate watchers)

scripts/
  ├── agent_health_check.py          ←── Manual agent liveness check (standalone)
  └── test_smc_strategy.py           ←── SMC strategy smoke tester (standalone)

docs/
  ├── important/SYSTEM_ARCHITECTURE.md   ←── This file (full system — all phases + all agents)
  ├── important/system_flow.md           ←── Phase 6 agent pipeline in detail (all 6 agents, all stages, inter-agent comms)
  ├── important/phase_7_system_flow.md   ←── Phase 7 pattern mining in detail (miner, window tuner, wisdom matrix)
  ├── important/phase_10_system_flow.MD  ←── Phase 10 pairs trading in detail (Z-score, cointegration, compound sim)
  └── recommendation/               ←── Architecture design proposals (human reference only)
      ├── DYNAMIC_PATTERN_ENSEMBLE.md
      ├── ENSEMBLE_BACKTEST_FRAMEWORK.md
      ├── REGIME_AWARE_ENSEMBLE.md
      └── AGENT_LONG_TERM_MEMORY.md

known_data_gaps.md                   ←── Published by Data Engineer (read by Researcher + Developer)
Pre-Analyse dataset/                 ←── User's real Binance futures CSV history (manual analysis only)
```

---

## 7. Phase 7 — Pattern Mining & Wisdom Matrix

**Entry:** `python phase_7/miner.py --strategy_id {id}`

```
settings.py (STRATEGY_LIBRARY)
       │
       ▼
phase_7/scripts/window_generator.py
  └── Splits history into windows:
       • Micro  — 1M, 2M, 3M, 4M     (volatility spikes, local anomalies)
       • Meso   — 3M, 4M, 6M         (consolidation, trend establishment)
       • Macro  — 1Y, 2Y, 3Y         (bull/bear/range cycles)
       │  Min bars required: 1M=50, 3M=100, 6M=150, 1Y=200, 3Y=600
       ▼
phase_7/scripts/regime_classifier.py
  └── Labels each window: TREND_UP / TREND_DOWN / CHOP_VOL / RANGE / etc.
       │
       ▼
phase_7/scripts/window_tuner.py
  └── Optuna search within each window → best params for that regime
       │  Caches results to raw_results/ — skips if already mined
       ▼
phase_7/data/wisdom_matrix.csv
  └── strategy_id | window_id | type | start_date | end_date |
      params (JSON) | roi | sharpe | regime | regime_score
```

**Dependency:** Phase 7 requires healthy `dataset/` parquets. Run Data Engineer health check before miner.

**Planned consumer:** `@crypto-pattern-agent` is a planned future agent (not yet built) that will consume `wisdom_matrix.csv` for regime-aware live paper trading. The skill folder `.gemini/skills/crypto-pattern-agent/` does not exist yet. Until it is built, Phase 7 output remains unmined. See `phase_7/README.md` for the intended design.

---

## 8. FreqAI Layer

**Location:** `freqai/` (full Freqtrade + FreqAI install)

**Role:** A parallel ML trading framework — independent from the 6-agent pipeline.

```
freqai/user_data/
  ├── strategies/      ← FreqAI-compatible strategy files
  ├── freqaimodels/    ← Trained ML models
  ├── data/            ← OHLCV in Freqtrade format
  ├── hyperopts/       ← Freqtrade hyperopt results
  ├── logs/            ← Freqtrade execution logs
  └── notebooks/       ← Jupyter analysis notebooks
```

**Integration status:** Standalone — the 6 agents do not read or write to `freqai/`. No bridge exists between FreqAI strategies and `strategy_backtest/settings.py`.

---

## 9. Data Infrastructure

### Parquet Structure

```
dataset/
  ├── BTC/  {1m, 5m, 15m, 30m, 1h, 4h, 1d}/spot_ohlcv.parquet
  │          4h/funding_rate.parquet
  ├── ETH/  {1m, 5m, 15m, 30m, 1h, 4h, 1d}/spot_ohlcv.parquet
  │          4h/funding_rate.parquet
  ├── BNB/  {1m, 5m, 30m, 1h, 4h, 1d}/spot_ohlcv.parquet  (no 15m)
  │          4h/funding_rate.parquet
  ├── SOL/  {1m, 5m, 30m, 1h, 4h, 1d}/spot_ohlcv.parquet  (no 15m)
  │          4h/funding_rate.parquet
  └── XRP/  {1m, 5m, 30m, 1h, 4h, 1d}/spot_ohlcv.parquet  (no 15m)
             4h/funding_rate.parquet

Macro folders (DXY, JPY, SPY, VIX) — DRL training only, NOT managed by Data Engineer.
```

**Required columns (spot_ohlcv):** `Open, High, Low, Close, Volume` (float64) + `taker_buy_base_vol` (float64) + `num_trades` (int64 or float64).

**Funding rate:** forward-filled from Binance 8h settlements to 4h bars. Required from 2023-01-01 for all 5 coins.

### Data Flow

| Component | Reads | Writes |
|---|---|---|
| Phase 0 scripts | Binance API | `dataset/` parquets |
| `strategy_backtest/engine.py` | `spot_ohlcv.parquet` + `funding_rate.parquet` | — |
| `phase_7/miner.py` | `dataset/` parquets | `wisdom_matrix.csv` |
| Data Engineer | `dataset/` parquets | Repaired parquets + `.bak` |
| Data Engineer | — | `known_data_gaps.md` |
| Researcher | `known_data_gaps.md` | — |
| Developer | `known_data_gaps.md` | — |

---

## 10. Agent Memory System

| Layer | File | Scope | Persists |
|---|---|---|---|
| Short-term | `session_memory.md` (per agent) | Current session (max 10 entries) | Session only |
| Global short-term | `.gemini/session_memory.md` | Cross-agent session summary | Session only |
| Long-term | `LTM.md` (per agent) | Agent-specific wisdom | Permanent |
| Global LTM | `.gemini/shared/GLOBAL_LTM.md` | System-wide patterns | Permanent |
| Message archive | `.gemini/shared/resolved_inbox.jsonl` | All processed messages | Permanent append-only |

**LTM entry format:** `[YYYY-MM-DD] | {PATTERN} | {CONSTRAINT}`

**Session memory rule:** Read at session start, prepend 1-line summary at finish. Max 10 entries kept (oldest trimmed).

### Mandatory Visibility Protocol (all agents)

Every action must produce 4 log entries:
1. **Activity Log** → `activity.log` (per-agent)
2. **Heartbeat** → `heartbeat.json` (stage + status, updated every 15s by background thread)
3. **Collaboration Ledger** → `.gemini/shared/AGENT_COLLABORATION.md`
4. **Changelog** → `.gemini/shared/SYSTEM_CHANGELOG.md` (`| TIMESTAMP | AGENT | FILE | WHAT | WHY |`)

---

## 11. Known Gaps & Status

### Fixed (2026-06-14)

| Gap | Fix Applied |
|---|---|
| `bug_patterns.md` not referenced in fullstack SKILL.md | Added to Toolbox section with instruction to read during TRIAGE |
| `alpha_research/concept_library/01_raw_ideas/` stale path in researcher scheduled task | Fixed in `agent_watcher.py` — now scans `factor_library/` for `status: QUEUED` cards |
| `@crypto-quant-researcher` old name still used in `main.py` code and 130+ log/memory entries | `@alpha-researcher` is the current name. All live code paths in `main.py` updated; all historical references in logs, session_memory, activity.log, resolved_inbox.jsonl updated (2026-06-14) |
| Phase 4 backtest crash (`NotImplementedError: dtype('<M8[us]')`) | pandas pickle version mismatch — fixed by regenerating `data/trade_data/` pickles via `phase_0/dl_trade_data.py` + fixing `processor_Dataset.py` float64 cast (2026-06-14) |
| No Tuner→Researcher feedback loop for failing strategies | Added Section 4a/4b to Tuner SKILL.md: mandatory `FACTOR_FAILURE_REPORT` inbox message + autopsy write on any ERROR strategy (2026-06-14) |
| `autopsy_report/` never written for early-stage crashes (TA_BAD_PARAM etc.) | Added `ON_FAIL: AUTOPSY` section to Developer STAGES.md covering all stages, not just WFO/PBO (2026-06-14) |
| `KNOWLEDGE_BASE.md` drifts manually (only 12 entries vs 103 strategies) | Created `crypto-fullstack/scripts/sync_knowledge_base.py` — auto-regenerates KB from scan_results.json + settings.py. Wired into Fullstack SKILL.md Stage [4/4] (2026-06-14) |
| `api_agent_console` used old agent name `quant-researcher` + was missing `alpha-developer` and `crypto-qa-tester` | Rewrote `main.py:449` with explicit `agent_hb_paths` dict — all 6 agents with correct paths (no `crypto-` prefix assumption for `alpha-*` agents) |
| `api_failure_report` never showed BAD/ERROR strategies from scan results | Fixed `main.py:1001–1020`: was iterating top-level dict keys instead of `sr['results']` list; also fixed `_scanned_at` → `scanned_at` key name |
| Phase 6 graveyard count always 0 for strategies from scan results | Fixed `main.py:1578–1588`: `build_pipeline_stats` had same broken dict iteration — now iterates `sr.get('results', [])` |
| Phase 6 monitor flagged researcher as "using fallback model" when running normally | Fixed `monitor_app.js:17`: `PREFERRED_MODELS.researcher` corrected from `'gemini-2.5-pro'` → `'gemini-3.1-pro-preview'` to match `agent_watcher.py` |
| Tuner agent card scan-grade badge always showed `0G 0M 0B` | Fixed `monitor_app.js:500`: badge read `sr.good/mediocre/bad` (lowercase) but `scan_results.json` uses uppercase `GOOD/MEDIOCRE/BAD` keys |
| Researcher model shown in gray in Model Usage table (no color) | Fixed `monitor_app.js:562`: `MODEL_COLORS` had `'gemini-2.5-pro'` (non-existent model) → corrected to `'gemini-3.1-pro-preview'` |
| `server.log` never updated — Flask stdout went to terminal, not log file | Fixed `main.py:15–22`: added Werkzeug file handler at startup so all HTTP access logs are appended to `server.log` regardless of how Flask is launched |
| `api_failure_report` surfaced stale SYSTEM_ERROR entries (e.g. Strategy 99 TA_RSI from 2026-06-03) alongside live failures | Fixed `main.py` failure report section: added 30-day recency cutoff — entries older than 30 days are skipped. Strategy 99 itself has no RSI bug; errors were ghost entries from an outdated finetune run |
| Developer Stage 2 built `check_regime()` as a phantom abstract method that doesn't exist in BaseStrategy | Removed `check_regime()` from all developer skill files. Correct pattern: inline boolean mask columns inside `generate_signals()` (e.g. `trend_up = df['Close'] > ema_200`). Confirmed from reading 4 concrete strategy files — none implement `check_regime()` as a method. |
| Developer had no knowledge of BaseStrategy's auto-kwargs, SIGNAL_PARAMS, or validate_params | Added BaseStrategy Contract to SKILL.md, STAGES.md Stage 2, and templates.md: auto-kwargs via setattr, SIGNAL_PARAMS purpose, validate_params override pattern, generate_signals must set self.df. |
| Developer Stage 5 ran WFO/PBO on default params (not optimized), causing false rejections | Added Optuna finetune step at Stage 5 (before WFO): baseline → register settings.py → run `finetune.py` → final backtest with best params → cross-asset → dev report. WFO now tests optimized strategy. |
| Stage 8 MANIFEST incorrectly said "update settings.py with WFO best params" | WFO is a stability test, not a param optimizer. Corrected Stage 8: verify settings.py already has Optuna best from Stage 5 — never overwrite. |
| Stage 5 hardcoded BTC/1h and 3-year date range regardless of strategy type | Stage 5 now reads primary coin and timeframe from card YAML. Date range from timeframe table: 5m→1yr, 15m→2yr, 1h/4h→3yr, 1d→4yr. Cross-asset uses same timeframe on other listed coins. |
| Developer library.py inventory missing — risk of reimplementing existing indicators | Added full indicator inventory table to templates.md (8 categories, 40+ functions). Stage 2 pre-build checklist requires running `grep "^def " strategy_backtest/library.py` first. |
| Researcher used `known_data_gaps.md` as a blocklist (it lists every pair as gapped) | Clarified: `known_data_gaps.md` logs partial gaps within datasets — it does NOT mean a pair is unusable. Added explicit Data Universe Guard: 5 coins (BTC, ETH, BNB, SOL, XRP), 5 timeframes (5m, 15m, 1h, 4h, 1d). |
| Researcher could propose cards with unsupported coins (DOGE, AVAX) or non-existent timeframes (2h, 8h) | Added coin/tf constraints to researcher Stage 2 EXTRACT_ALPHA: `coins:` and `timeframes:` YAML fields must only use the supported data universe. |

### Fixed (2026-06-15)

| Gap | Fix Applied |
|---|---|
| Sequential regex renaming script caused cascading key corruption in `settings.py` (strategies disappeared due to duplicate dict keys silently dropped by Python) | Restored from `.bak` using single-pass `re.sub` callback. All 102 strategy IDs renumbered 1–102 with no gaps. |
| 8 real strategy classes existed as `.py` files but were never registered in `settings.py` (invisible to backtest pipeline) | Registered IDs 103–110: DynamicVWAPATRScalperStrategy, RSIDivergenceReversalStrategy, RSIReversionStrategy, RsiEmaCrossoverStrategy, SqueezeMomentumStrategy, TightBollingerScalperStrategy, VolumePriceCorrelationExtremasStrategy, TripleConfirmFVMAStrategy |
| `calc_rsi(df, ...)` bug in IDs 105 & 106 (passed full DataFrame instead of `df['Close']` Series to TA-Lib) | Fixed both strategy files: `calc_rsi(self.df['Close'], ...)` |
| No mechanism to catch unregistered strategy classes — agents could create `.py` files without updating `settings.py` | Created `check_registration.py` guard script. Wired into tuner SKILL.md Stage [1/4] and alpha-developer SKILL/STAGES/PROTOCOLS Stage [8/8] MANIFEST. |
| alpha-developer PROTOCOLS.md was outdated (said "Register at Stage 8" instead of Stage 5) and had no `scan_all.py` step | Updated PROTOCOLS.md: Stage 5 now says "register NOW", Stage 8 says "run scan_all.py + classify_strategies.py". Added ON_FAIL note: never remove settings.py entry. |
| alpha-developer STAGES.md AUTOPSY section didn't explicitly preserve settings.py entry or update scan_results.json | Updated AUTOPSY: "KEEP settings.py entry — do NOT remove it"; added `scan_all.py` + `classify_strategies.py` mandatory step even on failure. |
| alpha-developer SKILL.md Stage 6/7 AUTOPSY same gap | Updated AUTOPSY_REPORT section: keep entry, run scan+classify, notify tuner. |
| QA tester had no test for unregistered classes or settings/scan_results ID sync | Added GROUP 5 (Registration Audit) to `system_test.py`: checks unregistered classes → routes to @alpha-developer; checks ID sync → routes to @crypto-strategy-tuner. |
| crypto-strategy-tuner SKILL.md Stage [1/4] AUDIT had no registration guard | Added `check_registration.py` call to Stage [1/4] description. |

### Fixed (2026-06-16) — Backtest Engine & Metrics Audit

A full audit of `engine.py`, `metrics.py`, `library.py`, and all strategy files was performed. All financial formulas (Sharpe, Sortino, Calmar, CAGR, Drawdown, Profit Factor, Expectancy, Monthly/Yearly returns, Slippage, Fee accounting) were verified correct. The following bugs were found and fixed:

| Gap | File | Fix Applied |
|---|---|---|
| Position sizing used `self.balance` when opening new positions, even if existing positions had large unrealized losses — could over-size entries during drawdown | `engine.py` | `_open()` now accepts `sizing_equity` param (balance + unrealized_long + unrealized_short). All callers (new entry + ADD) compute current equity and pass it in. New positions are now correctly sized against true wealth. |
| Liquidation check used stale entry notional (`long_ntl + short_ntl`) as the margin threshold — threshold drifted from reality as price moved away from entry | `engine.py` | Liquidation threshold now uses `qty × current_price` (market notional). Liquidation price solved analytically: `P = (balance − long_qty×entry_L + short_qty×entry_S) / ((long+short)×mm − net_qty)`, then clamped to bar's Low–High. |
| Hedge-mode trade pairing used a single `current_entry` variable — in strategies that hold long AND short simultaneously, SELL entry fees were absorbed into the long's accumulator and EXIT_SHORT was never counted as a closed trade | `metrics.py` | Replaced with `long_entry_rec / long_entry_fees` and `short_entry_rec / short_entry_fees` tracked independently. Each EXIT_LONG pairs with `long_entry_rec`; each EXIT_SHORT pairs with `short_entry_rec`. Trade count, Win Rate, and Expectancy are now correct for all hedge-mode strategies (104, 105, 107…). |
| Annual return (CAGR) used `365` days as the exponent while `bars_per_year` (used in Sharpe annualisation) used `365.25` — inconsistency in the same file | `metrics.py` | Changed CAGR exponent to `365.25` to match. Impact ~0.013%/yr, negligible, but now internally consistent. |
| `long_reversal` computed with `pct_change(N).shift(-N)` — look-ahead bias (read N bars into the future) | `multi_tf_momentum_reversal_strategy.py` | Changed to `pct_change(N)` (backward-looking only). No P&L impact because `long_reversal` was never used in signal conditions, but data leak removed. |
| `detect_swing_high_low` used `rolling(window=2*lookback+1, center=True)` — labelling bar `i` as a swing pivot required seeing `lookback` future bars, introducing look-ahead bias in any strategy that uses this function | `library.py` | Changed to backward window: `rolling(2*lookback+1)` + `shift(lookback)`. Semantics: `is_swing_high[i]` is now True at the **confirmation bar** `i` (when `lookback` bars have passed since the pivot at `i-lookback`). Fully causal — no future data required. |
| `ict_holy_trinity_confluence_strategy.py` used `df['High'].where(is_swing_high).ffill()` — after the library fix, this extracted the confirmation bar's High instead of the pivot bar's High | `ict_holy_trinity_confluence_strategy.py` | Changed to `df['High'].shift(swing_lookback).where(is_swing_high).ffill()` — correctly retrieves the pivot bar's actual High/Low value and forward-fills from confirmation time onward. |
| Strategy 110 (TripleConfirmFVMAStrategy) finetune produced degenerate MACD params (fast=13, slow=22, gap 9) and tp_atr_mult=1.29 → Sharpe -0.67 vs baseline -0.12 | `triple_confirm_fvma_strategy.py` | Added `validate_params` classmethod (rejects slow−fast < 8 and tp_atr_mult < sl_atr_mult). Raised `macd_slow` floor to 20 and `tp_atr_mult` floor to 1.5 in `OPTIMIZATION_RANGES`. Re-run produced Sharpe -0.05. All 8 strategies (103–110) now have final finetuned params in `settings.py`. |

**Verification results (post-fix):**
- All 8 strategies 103–110: zero NaN signals ✓
- All 8 strategies 103–110: balance never goes negative ✓
- Balance reconstruction check: `initial − entry_fees + Σ(exit_net_PnL) = final_equity` — exact match ($1906.78 = $1906.78) ✓
- Slippage: long entries fill higher, long exits fill lower; short entries fill lower, short exits fill higher — all adverse ✓
- `multi_tf_rsi_divergence_strategy.py` `_detect_divergence`: uses its own implementation with signals placed at `i+w` (confirmation time) — already causal, no fix needed ✓

**Note for agents — `detect_swing_high_low` interface change:** If you use `detect_swing_high_low(df, lookback=N)` from `library.py`, the returned booleans now mark the **confirmation bar** (not the pivot bar). To extract the correct pivot price, use `df['High'].shift(N).where(is_swing_high).ffill()` — NOT `df['High'].where(is_swing_high).ffill()`.

### Fixed (2026-06-17)

| Gap | Fix Applied |
|---|---|
| Strategy #75 (`FUNDING_RATE_MEAN_REVERSION_XRP_4H`) silently deleted by a background agent edit between 11:06–11:23 | Restored from `.bak` (last good snapshot at 11:06). Root cause: agents backed up before edit but never validated syntax after — a corrupt edit went undetected for 17 min until Flask tried to reload `settings.py` |
| No post-edit syntax validation in agent SKILL.md files — agents could corrupt `settings.py` silently | Added mandatory post-edit AST check to Safety section of all 3 editing agents: `alpha-developer`, `crypto-fullstack`, `crypto-strategy-tuner`. Rule: after any `settings.py` edit, run `python3 -c "import ast; ast.parse(open('strategy_backtest/settings.py').read()); print('syntax OK')"` — if it fails, restore `.bak` immediately |
| Phase 4 backtest tab: strategy rankings showed internal id string (e.g. `SCAN_NEW_TEST_STRATEGY`) instead of class name | Added `'class': cfg['class']` to `api_strategy_backtest()` results in `main.py`; updated 4 locations in `phase_4/dashboard/app.js` (comparison legend, rankings table, detail panel title, equity chart trace) to use `s.class` |
| Phase 4 backtest tab: `_stratListLoaded = true` was set at the top of `loadStrategyList()` before fetch completed — if Flask was down during page load, the flag was permanently `true` and switching back to the Strategy tab never retried | Moved `_stratListLoaded = true` into the `.then()` success handler; added `_stratListLoaded = false` in the `.catch()` handler so a failed load retries on next tab switch |
| 9 stale `RUNTIME_ERROR_DETECTED` inbox files in `crypto-fullstack/inbox/` (all from pre-fix `settings.py` syntax error at line 977) | Moved all 9 to `dead_letter/` — errors were resolved before they were processed |
| `system_flow.md` QA section missing GROUP_5 (registration audit) and showing [1/4]–[4/4] instead of [1/5]–[5/5] | Updated `system_flow.md` QA agent section to [1/5]–[5/5] with GROUP_5 (unregistered class check + settings/scan_results ID sync) and proper FINALIZE stage |
| `system_flow.md` ON_FAIL AUTOPSY did not say to preserve settings.py entry or run `scan_all.py` | Updated ON_FAIL block: "KEEP the settings.py entry — do NOT remove it" + mandatory `scan_all.py + classify_strategies.py` step after any AUTOPSY |

### Fixed (2026-06-18) — 26-Rule Rulebook & Backtest Validation Layer

A full compliance audit of the rule-based backtest system against the 26-rule Rulebook standard was performed. Four improvements were implemented:

| Gap | File | Fix Applied |
|---|---|---|
| `metrics.py` missing 6 validation metrics required by the Rulebook | `strategy_backtest/metrics.py` | Added: **DSR p-value** (T2-04, Bailey-López de Prado deflated Sharpe — `p = 1 − Φ(SR / σ_SR)`); **Cost Ratio** (T1-07, fees / |net_profit|); **Worst Daily Loss** (T1-06, min daily equity pct-change); **Monthly GTP** (T2-06, net_profit / sum of losing months); **Weekday vs Weekend Sharpe** (T3-04, split daily returns by dayofweek); **Regime MDD** (T3-03, per-regime MDD for bear_2022 / range_2023 / bull_2024 slices). All metrics are computed in `compute_metrics()` and appear in backtest output automatically. |
| `settings.py` had 20+ strategies with 1-year date windows (`2023-01-01 → 2024-01-01`) — all failing T0-01 (≥ 3 years required) | `strategy_backtest/settings.py` | All short-window entries extended to `2021-01-01 → 2026-05-31`. Three failed/rejected strategies removed (IDs 51, 55, 101). Duplicate dict keys 26/27/28 (first occurrences silently lost by Python) renamed to 200/201/202. Strategy 78 start date corrected. Total: **119 strategies** (previously 110 tracked + recovered duplicates). |
| `wfo_runner.py` was a 40-line stub that only printed annual Sharpe for one hardcoded strategy (ID 108). No IS/OOS split, no WF efficiency, not general-purpose | `strategy_backtest/scripts/wfo_runner.py` | **Complete rewrite** into an 8-fold anchored expanding-window walk-forward framework. General for any strategy ID. Computes per-fold IS/OOS Sharpe, WF efficiency = mean(OOS_Sharpe / IS_Sharpe) (T2-01), IS→OOS decay (T2-02), OOS/IS MDD ratio (T1-08), positive OOS fold count. PASS thresholds: efficiency ≥ 0.50, MDD ratio ≤ 1.50, decay ≤ 0.50. CLI: `--strategy`, `--folds`, `--save`. |
| No automated 26-rule compliance validator existed for strategy_backtest strategies | `strategy_backtest/validator.py` | **New file.** Full 26-rule Rulebook engine covering: T0-01 data integrity (2,000-bar minimum), T1 fatal gates (Sharpe, return, MDD, win rate, PF, trade count, worst daily loss, cost ratio, WFO, lookahead probe, regime survival), T2 quality gates (WF efficiency, OOS decay, PBO via param variants, DSR, random-label control, GTP/PF OR condition), T3 warnings (block bootstrap MC, param sensitivity ±10%, regime MDD, weekend Sharpe, truncation test), Crypto Pack (funding impact, news blackout ±7 days around LUNA/FTX/ETF events, vol-regime Sharpe). Scores out of 100; APPROVED if ≥ 70% and all T1 gates pass. CLI: `--strategy`, `--folds`, `--quick` (skips PBO + sensitivity), `--save`. |

**Rulebook coverage (19/26 fully correct; 7 with crypto-appropriate thresholds):**
- T1-03 MDD: 50% threshold (standard says 20% — unrealistic for 10–30× leveraged crypto futures)
- T1-06 Worst daily loss: −20% threshold (standard says −4% — too strict for leveraged positions)
- T1-07 Cost ratio: 50% threshold (standard says 30% — equity-market standard)
- T0-02 min bars, T1-05 trade count, T2-06 OR condition: all structurally correct with crypto-appropriate values

### Remaining Open Gaps

| Gap | Impact | Status |
|---|---|---|
| **`@crypto-pattern-agent` not yet built** | Planned Phase 7 live-trading agent — `wisdom_matrix.csv` consumer. Documented in `phase_7/README.md` as future work | Planned, not a bug |
| **FreqAI not wired to agents** | Models trained in `freqai/` are not graded or tracked by the pipeline | Intentional separation or future work |
| **Cross-asset sections empty in dev_reports** | 27 current dev_reports show "⏳ Pending cross-asset run" in section 2 | Tuner should fill when running cross-asset scans |
| **DRL actor.pth not integrated with rule-based pipeline** | Two separate optimization outputs (neural net vs rule-based strategies) with no bridge | May be intentional two-track design |
| **`KNOWLEDGE_BASE.md` strategy status drifts** | Shows LIVE/PAPER/BENCH per strategy but no agent writes this automatically | Manual maintenance required |
| **`research_results/` folder is stale** | Researcher no longer writes here; actual output is `factor_library/` cards | Harmless but confusing |

### Single Points of Failure

| Component | Risk | Mitigation |
|---|---|---|
| `strategy_backtest/settings.py` | Corruption = 110 strategies lost | `settings.py.bak` created before every agent edit; `check_registration.py` guard prevents silent class omissions; post-edit `python3 -c "import ast; ast.parse(...)"` validation in all 3 agent SKILL.md files — agents must restore from `.bak` if syntax check fails |
| Gemini API quota | All agents stop | Model cascade (Pro → Flash → Flash-Lite-Preview → Flash-Lite) |
| `dataset/BTC/1h/spot_ohlcv.parquet` | Corruption = most backtests fail | Data Engineer creates `.bak` on next repair cycle (no `.bak` currently — all deleted 2026-06-14) |
| Flask `main.py` crash | No UI control (agents keep running independently) | Watcher is independent of Flask |

---

## 12. Entry Points — How to Start Everything

### Start the Full System

```bash
# Terminal 1: Flask master dashboard
python main_controller/main.py
# → http://127.0.0.1:5001

# Terminal 2–7: One watcher per agent
python Crypto_Agent/agent_watcher.py researcher
python Crypto_Agent/agent_watcher.py developer
python Crypto_Agent/agent_watcher.py tuner
python Crypto_Agent/agent_watcher.py data
python Crypto_Agent/agent_watcher.py qa
python Crypto_Agent/agent_watcher.py fullstack
```

### Run Specific Phase Scripts

```bash
# Phase 1: CPCV hyperparameter search (most rigorous)
python core/optimize_cpcv.py

# Phase 4: Backtest DRL model on unseen data
python phase_4/backtest.py

# Phase 5: PBO overfit check
python phase_5/pbo.py

# Phase 7: Mine regime patterns for a specific strategy
python phase_7/miner.py --strategy_id 86

# Scan all strategies (Tuner)
./venv/bin/python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py

# Finetune a specific strategy (Optuna 150 trials)
./venv/bin/python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id 75

# Grid-search optimize a strategy
./venv/bin/python strategy_backtest/optimizer/optimize_t3_nexus_stiff.py

# Single strategy backtest
./venv/bin/python strategy_backtest/run_backtest.py --strategy 75

# Manual agent liveness check
python scripts/agent_health_check.py

# Zombie sweep (clear dead watcher PIDs)
./venv/bin/python .gemini/skills/crypto-fullstack/scripts/zombie_sweep.py

# Chaos test (Flask API route sweep)
./venv/bin/python .gemini/skills/crypto-fullstack/scripts/chaos_test.py
```

### Trigger an Agent via Inbox

```bash
# Force Researcher to start research cycle
cat > .gemini/skills/alpha-researcher/inbox/$(date +%s)_from_user_START.json << 'EOF'
{"trigger": "START", "priority": "HIGH", "from": "user", "ts": "2026-06-14T00:00:00Z"}
EOF

# Force Tuner to run a full rescan
cat > .gemini/skills/crypto-strategy-tuner/inbox/$(date +%s)_from_user_FORCE_RESCAN.json << 'EOF'
{"trigger": "FORCE_RESCAN_NOW", "from": "user"}
EOF
```

---

*Last updated: 2026-06-18 — 122 strategies in settings.py (IDs 1–119 + 200/201/202 recovered duplicates, minus removed failures). Fixes (session 1): bug_patterns.md reference, stale researcher path, crypto-quant-researcher rename, .bak cleanup, Phase 4 pickle fix, Tuner/Developer feedback loops, KB sync script, 7 dashboard bugs, server.log Werkzeug file handler, failure_report 30-day stale-error filter. Fixes (session 2): Developer agent — removed phantom check_regime(), added BaseStrategy contract (auto-kwargs, SIGNAL_PARAMS, validate_params, self.df rule), added Optuna finetune at Stage 5 before WFO, corrected Stage 8 (WFO does not produce best params), Stage 5 coin/tf now driven by candidate card YAML, added library.py indicator inventory, Stage 2 pre-build checklist. Researcher agent — replaced Data-Feasibility Guard with Data Universe Guard (5 coins, 5 tfs explicit), added coin/tf constraints to card YAML writing. Fixes (session 3): renumbered IDs 1–102 (single-pass fix after regex cascade corruption), registered 8 missing strategy classes (IDs 103–110), fixed calc_rsi(df) bug in IDs 105/106, created check_registration.py guard, updated alpha-developer STAGES/PROTOCOLS/SKILL (ON_FAIL preserve settings.py + scan), updated crypto-strategy-tuner SKILL Stage 1 (registration guard), added QA GROUP 5 (registration audit + settings/scan sync check). Fixes (session 4 — backtest engine audit): engine.py — position sizing now uses equity (not just balance) preventing over-sizing when open positions have unrealized losses; liquidation threshold now uses market notional (qty×price) not stale entry notional; metrics.py — hedge-mode trade pairing fixed (long/short entries tracked independently, EXIT_SHORT now correctly counted); CAGR exponent changed 365→365.25 for consistency with Sharpe annualisation; multi_tf_momentum_reversal_strategy.py — look-ahead removed from long_reversal; library.py detect_swing_high_low — replaced center=True with causal backward window (is_swing_high[i] now marks confirmation bar not pivot bar); ict_holy_trinity_confluence_strategy.py — updated pivot value extraction to use shift(lookback); strategy 110 finetuned with validate_params guard + raised OPTIMIZATION_RANGES floors (Sharpe -0.12 → -0.05). All 8 strategies 103–110 verified: zero NaN signals, balance never negative, balance reconstruction exact. Fixes (session 5): strategy #75 restored from .bak after silent agent deletion; post-edit AST syntax validation added to all 3 agent SKILL.md files (alpha-developer, crypto-fullstack, crypto-strategy-tuner) — agents must validate settings.py after every edit and restore .bak if syntax fails; Phase 4 strategy rankings fixed (class name now shown instead of internal id); Phase 4 _stratListLoaded bug fixed (set only on success, cleared on failure, enabling retry); 9 stale inbox errors moved to dead_letter/; system_flow.md QA section updated to 5 stages (added GROUP_5 registration audit + FINALIZE); system_flow.md ON_FAIL updated to preserve settings.py entry + run scan_all.py.*


---

## 13. Backtest Engine & Verdict System (SignalHive Standard v1.0)
*Added: July 2026*

### Overview

Crypto-RL's backtest engine now implements the **SignalHive 27-rule rulebook** for professional-grade strategy validation. Every backtest run is evaluated against:

- **T0 Prerequisites** (2 rules): Data integrity, reproducibility
- **T1 Fatal Gates** (11 rules): Profitability, risk limits, sample size, cost efficiency, walk-forward, lookahead, leverage
- **T2 Blocking Gates** (5 rules): Walk-forward efficiency, OOS decay, overfitting probability, statistical significance, P&L structure
- **T3 Robustness Advisories** (7 rules): Hit rate, parameter robustness, bootstrap confidence, truncation consistency
- **CR Crypto Pack** (3 rules): Funding P&L, news blackout resilience, weekend/weekday Sharpe divergence

**Verdict outcomes:**
- `REJECTED`: T0 prerequisite failed
- `FAIL`: T1, T2, or CR gate failed
- `PASS_WITH_WARNINGS`: T3 advisories only
- `PASS`: All gates cleared

**Score formula:** `(T1_pass × 40) + (T2_pass × 30) + (T3_count × 4) + (CR_pass × 10)` = 0–100 points

### Files

| File | Purpose |
|---|---|
| `strategy_backtest/engine.py` | Bar-by-bar backtesting with position management, funding rates, liquidation checks |
| `strategy_backtest/risk.py` | Position sizing with **frequency-based risk defaults** (50% HFT, 30% intraday, 15% swing, 5% position) |
| `strategy_backtest/cost_calculator.py` | **Square-root market impact slippage** + fees + borrow + funding (all-in cost model) |
| `strategy_backtest/frequency_utils.py` | Auto-detect bar frequency, classify tier (HFT/Intraday/Swing/Position), map adaptive thresholds |
| `strategy_backtest/verdict_engine.py` | 27-rule verdict system with early-stopping logic and SignalHive-compliant scoring |
| `strategy_backtest/metrics.py` | Compute Sharpe, Sortino, drawdown, DSR p-value, and trade statistics |
| `strategy_backtest/run_backtest.py` | Main runner, integrates all components, supports multi-coin portfolio mode |

### Key Changes from Previous System

#### 1. **Slippage Model** (CRITICAL)

**Old:** Flat percent slippage (e.g., 0.05% fixed)
```python
price = raw_price * (1.0 + slippage_pct * side)  # Fixed 0.05%
```

**New:** Square-root market impact (SignalHive standard)
```python
# slippage = max(0.5 bps, 8 × √(qty/vol × 100))
slippage = max(0.000005, 8 * np.sqrt((notional / volume) * 100) / 10000)
```

Impact: A 1 BTC order on a 100 BTC volume bar now costs ~1.8 bps, not flat 5 bps. Realistic for real trading.

#### 2. **Risk Per Trade Defaults** (CRITICAL)

**Old:** Hard-coded 0.10 (10%) for all strategies
**New:** Frequency-based adaptive (SignalHive standard)

| Frequency | Tier | Risk % | Rationale |
|---|---|---|---|
| 5m, 15m | HFT | 50% | Tight stops, many trades |
| 30m | Intraday | 30% | Moderate holding time |
| 1h, 4h | Swing | 15% | Wider stops, fewer trades |
| 1d+ | Position | 5% | Multi-day holding, market-neutral |

```python
rm = RiskManager(frequency='4h')  # Auto-defaults to 0.15 (15%)
```

Impact: 4h strategies now pass MDD gates; strategies designed for proper frequency band survive validation.

#### 3. **Cost Ratio Formula** (IMPORTANT)

**Old:** `cost_ratio = total_fees / abs(net_profit)`
**New:** `cost_ratio = (fees + slippage + borrow + funding_paid) / gross_pnl`

- Uses `gross_pnl` (winning trades only), not net profit
- Includes all costs: taker fees (4 bps), slippage, short borrow (3 bps/day), funding payments
- Adaptive threshold: 50% HFT → 15% swing → 5% position

```python
from strategy_backtest.cost_calculator import CostCalculator
cc = CostCalculator()
slippage = cc.calculate_slippage(qty, price, volume)  # per-trade realistic
```

#### 4. **Frequency-Based Adaptive Thresholds** (IMPORTANT)

All major rules now scale by frequency. Example for T1-10 (cost ratio):

```python
# HFT (5m, 15m):    cost_ratio_max = 50%
# Intraday (30m):   cost_ratio_max = 30%
# Swing (1h, 4h):   cost_ratio_max = 15%  ← Most strict (crypto 4h is here)
# Position (1d+):   cost_ratio_max = 5%   ← Strictest
```

Automatic via `frequency_utils.get_threshold()`:
```python
threshold = get_threshold(frequency='4h', rule_key='cost_ratio_max')  # Returns 0.15
```

#### 5. **Verdict Logic** (STRUCTURAL)

**Old:** All rules weighted equally, verdict not early-stopping

**New:** SignalHive early-stopping (strict → lenient)
```
T0 fail (prerequisite)     → REJECTED (stop immediately)
T1 fail (any fatal gate)   → FAIL (stop immediately)
T2 fail (any blocking gate)→ FAIL (stop immediately)
CR fail (crypto-only)      → FAIL (stop immediately)
T3 only (advisories)       → PASS_WITH_WARNINGS
All clear                  → PASS
```

Score formula (exact):
```
score = (T1_all_pass × 40) + (T2_all_pass × 30) + (T3_count_pass × 4) + (CR_all_pass × 10)
      = 0 to 100 points
```

#### 6. **Multi-Coin Portfolio Mode** (NEW)

Strategies can now run in **portfolio mode** (one equity book, all coins interleaved) or **per_coin mode** (isolated book per coin, one verdict each).

```python
# Portfolio: all coins share equity, 1 verdict
from strategy_backtest.run_backtest import run_strategy
result = run_strategy(cfg, mode='portfolio', symbols=['BTCUSDT', 'ETHUSDT'])
# → equity_curve, trades, metrics (aggregated across all coins)

# Per-coin: separate books
result = run_strategy(cfg, mode='per_coin', symbols=['BTCUSDT', 'ETHUSDT'])
# → [result_BTC, result_ETH] (separate verdict per coin)
```

**Critical warning:** A single-coin strategy submitted in portfolio mode with multiple coins will silently scramble (entries on BTC, exits on ETH). Always verify strategy state is keyed by `event.symbol` for portfolio mode.

### Verdict Engine (`verdict_engine.py`)

Main entry point for generating verdicts:

```python
from strategy_backtest.verdict_engine import VerdictEngine

engine = VerdictEngine(frequency='4h')
result = engine.check_all(
    metrics_dict=compute_metrics(...),
    equity_curve=equity,
    trades=trades,
    timestamps=timestamps,
    cfg=cfg,
    is_crypto=True,
)

print(result)
# {
#   'decision': 'PASS',
#   'score': 82.5,
#   'blocking_rules': [],
#   'outcomes': [
#     {'rule_id': 'T1-01', 'tier': 'T1', 'passed': True, 'summary': 'Sharpe Ratio = 0.73 (≥ 0.50)'},
#     ...
#   ]
# }
```

### Example: Running a Strategy with Verdicts

```bash
# Simple single-coin run with verdict
python strategy_backtest/run_backtest.py --strategy 86 --date_from 2023-01-01 --date_to 2026-01-01

# Output includes:
#   Loaded 1256 bars (2023-01-01 → 2026-01-01)
#   Strategy : 86
#   Desc : Multi-timeframe mean-reversion
#   Class : SID_86_Strategy | TF: 4h | Coin: BTCUSDT
#   Period : 2023-01-01 → 2026-01-01
#   ============================================================
#   
#   ── Results ──
#   Total Return: 437.2%
#   Annual Return: 28.4%
#   Sharpe Ratio: 0.73
#   Max Drawdown: 14.2%
#   Profit Factor: 1.84
#   Win Rate: 47.1%
#   Total Trades: 156
#   Cost Ratio: 13.6%
#   
#   ── 27-Rule Verdict ──
#   Decision: PASS
#   Score: 87/100
#   
#   T1 Fatal Gates (all pass → +40):
#     ✓ T1-01: Sharpe Ratio = 0.73 (≥ 0.50)
#     ✓ T1-02: Total Return = 437.2% (> 0%)
#     ✓ T1-03: Max Drawdown = 14.2% (≤ 20%)
#     ✓ T1-04: Worst Daily Loss = -5.2% (≥ -6.0% for swing)
#     ✓ T1-05: Profit Factor = 1.84 (≥ 1.0)
#     ✓ T1-06: Win Rate = 47.1% (≥ 35% for swing)
#     ✓ T1-07: Total Trades = 156 (≥ 30)
#     ✓ T1-08: Liquidations = 0 (0)
#     ⚠ T1-09: Lookahead probe SKIPPED
#     ✓ T1-10: Cost Ratio = 13.6% (≤ 15% for swing)
#     ✓ T1-11: Losing Years = 2 (≤ 4)
#   
#   T2 Blocking Gates (all pass → +30):
#     ✓ T2-01: Walk-Forward Efficiency = 0.67 (≥ 0.5)
#     ✓ T2-02: OOS Sharpe Decay = 28% (≤ 50%)
#     ✓ T2-04: DSR p-value = 0.0023 (< 0.05)
#     ✓ T2-06: Monthly GTP = 1.42 (≥ 1.0)
#   
#   T3 Robustness (5/6 pass → +20):
#     ✓ T3-01: Hit Rate = 47.1% (≥ 35%)
#     ✓ T3-03: Bootstrap 5th% Sharpe = 0.54 (> 0)
#     ✓ T3-04: Monte Carlo Median Return = +18.2% (> 0%)
#     ✓ T3-05: Truncation Check: 0 diff
#     ✗ T3-06: No Losing Years (advisory, no score)
#   
#   CR Crypto Pack (all pass → +10):
#     ✓ CR-01: Funding P&L Ratio = 12% (≤ 50%)
#     ✓ CR-03: Weekend/Weekday Sharpe = 0.81 (within ±100%)
```

### Migration from Old to New System

If upgrading from the previous version:

1. **Check risk_per_trade defaults:**
   ```python
   # Old: all use 0.10
   # New: auto-set per frequency (5m→50%, 15m→50%, 30m→30%, 1h→15%, 4h→15%, 1d→5%)
   # Action: Remove hard-coded 0.10 from settings.py, let RiskManager auto-detect
   ```

2. **Check slippage in settings:**
   ```python
   # Old: slippage_pct=0.0005 (0.05%)
   # New: slippage_pct=0.0 (deprecated, use CostCalculator)
   # Action: Set to 0.0, update any custom slippage logic to use CostCalculator.calculate_slippage()
   ```

3. **Check cost_ratio calculations:**
   ```python
   # Old: cost_ratio = fees / net_profit
   # New: cost_ratio = (fees + slippage + borrow + funding) / gross_pnl
   # Action: Update any references to align with new formula (uses gross_pnl)
   ```

4. **Run verdicts with VerdictEngine:**
   ```python
   # Old: Manual rule checks scattered across validator.py
   # New: Use VerdictEngine.check_all() for unified 27-rule verdict
   from strategy_backtest.verdict_engine import VerdictEngine
   engine = VerdictEngine(frequency='4h')
   verdict = engine.check_all(...)
   ```

### Next: PortingStrategies to SignalHive

Once all 27 rules pass locally:

1. Export strategy to SignalHive API format:
   - `strategy.py` (Strategy subclass with `on_bar()` method)
   - `profile.yaml` (frequency, symbols, leverage, capital)

2. Upload via SignalHive API:
   ```bash
   export BT_TOKEN=sk_bt_...
   curl -X POST http://47.237.70.198:5300/api/backtest/v1/strategies \
     -H "Authorization: Bearer $BT_TOKEN" \
     -F "strategy.py=@strategy.py" \
     -F "profile.yaml=@profile.yaml"
   ```

3. Run backtest:
   ```bash
   curl -X POST http://47.237.70.198:5300/api/backtest/v1/runs \
     -H "Authorization: Bearer $BT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"strategy_id":"str_...", "symbols":["BTCUSDT"], "mode":"per_coin"}'
   ```

4. Poll verdict:
   ```bash
   curl http://47.237.70.198:5300/api/backtest/v1/runs/run_.../verdict \
     -H "Authorization: Bearer $BT_TOKEN"
   ```

---

## Appendix: Backtest Execution Mechanics & Realism
*Update: June 2026*

The Crypto-RL Backtesting Engine (`strategy_backtest/engine.py`) employs standard institutional "Intra-bar Interpolation" to process Stop-Loss (SL), Trailing Stop (TS), and Take Profit (TP) orders.

### 1. Intrabar Priority (Pessimistic Execution Bias)
Because OHLC data cannot provide the exact tick sequence of a single bar, it is possible for a bar's High to breach a Take Profit and its Low to breach a Stop Loss simultaneously.
* **Standard Rule:** Crypto-RL uses a **Pessimistic Execution Bias**. Each strategy's `manage_trade()` checks the Stop-Loss / Trailing Stop condition first. If both SL and TP are breached within the same bar, the SL fills first. This ensures backtest results do not overstate profitability.

### 2. The Gap-Through Guard
Crypto-RL natively handles market gaps (e.g., when the `Open` price of a bar skips entirely past a resting stop-market or limit order):
* **Stop Orders (SL / TS):** If a bar opens past the stop-loss level, the fill price is downgraded to the exact `Open` price.
* **Limit Orders (TP):** If a bar opens past the take-profit level, the limit order is upgraded to fill at the `Open` price.

### 3. "Look-Ahead Bias" vs Intra-Bar Interpolation
Using the `Low` of the current bar to detect an intrabar Stop-Loss breach—and executing exactly at that exact level—is **NOT** Look-Ahead Bias. It correctly simulates an exchange holding a Stop-Market order. Delaying market orders until the Bar Close (as seen in rudimentary frameworks like `backtesting.py`) creates unrealistic "Pessimistic Execution Bias." Crypto-RL simulates exact exchange execution semantics without looking at the next bar's data.
