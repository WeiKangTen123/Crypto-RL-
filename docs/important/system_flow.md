# Crypto-RL — Agentic System Flow
> Last updated: 2026-06-18
> Track B (Phase 6) agentic pipeline — all 6 agents, all stages, all inter-agent communication

---

## THE 6 AGENTS

| Agent | Role | Schedule | Primary Script |
|---|---|---|---|
| `@alpha-researcher` | Discovers new strategies from web/queue, writes Candidate Cards | Every 360 min | Web search + file writes |
| `@alpha-developer` | Builds, backtests, and validates strategy code (7-stage pipeline) | Every 360 min | strategies/, finetune.py, wfo.py |
| `@crypto-strategy-tuner` | Grades all strategies, runs Optuna rescue, promotes GOOD | Every 120 min | scan_all.py, finetune.py |
| `@crypto-data-engineer` | Keeps parquet data fresh; fulfils data requests from other agents | Every 360 min | health_scout_v2.py, incremental_fetcher.py |
| `@crypto-qa-tester` | Runs automated tests on Flask, strategies, and data linkage | Every 720 min | system_test.py |
| `@crypto-fullstack` | Patches bugs in infrastructure, Flask routes, dashboards | Every 720 min | main.py, bug_patterns.md |

---

## TOP-LEVEL PIPELINE FLOW

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                     DISCOVERY INTAKE (3 channels)                    │
 │                                                                      │
 │  ① WEB RESEARCH          ② QUEUE PICKUP         ③ CROSS-FERTILIZE   │
 │  Tier 1: TradingView      QUEUED cards in         GOOD strategy →    │
 │          GitHub           factor_library/          related variants  │
 │  Tier 2: arXiv · SSRN    interest: High first     from Tuner signal  │
 │  Tier 3: Twitter/Reddit                                              │
 └──────────────────────┬───────────────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐        ┌─────────────────────────────┐
            │  @alpha-researcher    │        │  @crypto-data-engineer       │
            │  [4-stage pipeline]   │◄──────►│  [BLOCKED card handling]     │
            │                       │        │  Fetches missing data types  │
            └──────────┬────────────┘        └─────────────────────────────┘
                       │
                       │  NEW_FACTOR_DISCOVERED (inbox)
                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  factor_library/  —  Candidate Cards  (112 total)        │
            │  status: QUEUED · IN_PROGRESS · VALIDATED · REJECTED     │
            └──────────────────────────┬───────────────────────────────┘
                                       │
                                       │  developer picks QUEUED card
                                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  @alpha-developer  —  8-Stage Build Pipeline              │
            │  [1] INGEST → [2] BUILD → [3] SYNTAX → [4] SMOKE →       │
            │  [5] DEV_REPORT → [6] WFO_EVO → [7] PBO_AUDIT →          │
            │  [8] MANIFEST                                             │
            └──────────────────────────┬───────────────────────────────┘
                                       │
                                       │  strategy registered in settings.py
                                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  strategy_backtest/settings.py  (119 strategies)         │
            │  Params = Optuna best (from finetune.py at Stage 5)      │
            └──────────────────────────┬───────────────────────────────┘
                                       │
                                       │  STRATEGY_READY (inbox)
                                       ▼
            ┌──────────────────────────────────────────────────────────┐
            │  @crypto-strategy-tuner  —  4-Stage Grader                │
            │  [1] AUDIT → [2] WORK_CYCLE → [3] REPORTING → [4] MANIFEST│
            └──────────────────────────┬───────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              🟢 GOOD (7)        🟡 MEDIOCRE (44)    🔴 BAD (59)
              Sharpe ≥ 1.0       Sharpe 0.3–1.0      Sharpe < 0.3
                    │                  │                  │
                    │            finetune.py        finetune.py
                    │            (rescue)           (rescue × 3)
                    ▼                                     │
             Paper Trading                          autopsy_report/
             (PAPER status)                        FACTOR_FAILURE_REPORT
                    │                              → @alpha-researcher
                    │
                    ▼
            ┌──────────────────────────────────────────────────────────┐
            │  ALWAYS ON — Support Layer                                │
            │                                                           │
            │  @crypto-data-engineer  ────  data freshness + requests   │
            │  @crypto-qa-tester      ────  test & route failures       │
            │  @crypto-fullstack      ────  infra bugs + Flask patches  │
            └──────────────────────────────────────────────────────────┘
```

---

## AGENT 1 — @alpha-researcher

**Schedule**: Every 360 min | **3-stage pipeline**

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [1/3] WEB_SEARCH (Model: gemini-3.1-pro-preview)                    │
  │                                                                     │
  │  Tier 1 (search first):  TradingView · GitHub freqtrade             │
  │  Tier 2 (concepts):      arXiv q-fin · SSRN                         │
  │  Tier 3 (optional):      Reddit r/algotrading                       │
  │                                                                     │
  │  Priority factor gaps:  funding rate MR · multi-TF divergence       │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [2/3] EXTRACT_ALPHA (Model: gemini-2.5-flash)                       │
  │                                                                     │
  │  DATA UNIVERSE GUARD (hard block):                                  │
  │    Supported coins: BTC · ETH · BNB · SOL · XRP  (5 only)          │
  │    Supported TFs:   5m · 15m · 1h · 4h · 1d     (5 only)           │
  │    Adapt foreign coins → nearest supported coin                     │
  │                                                                     │
  │  Available columns (no request needed):                             │
  │    OHLCV · taker_buy_base_vol · num_trades  (all 5 coins × 5 TF)   │
  │    funding_rate  (all 5 coins, 4h only)                             │
  │                                                                     │
  │  DECISION:                                                          │
  │    ✅ All columns available → proceed to [3/3]                       │
  │    ⛔ Needs data → Send DATA_REQUEST to @crypto-data-engineer inbox  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [3/3] HYPHO_REPORT_&_INDEX_SYNC (Model: gemini-2.5-flash)           │
  │                                                                     │
  │  Skip condition: If Stage 2 found no novel math, STOP.              │
  │                                                                     │
  │  Extract pure mathematical signal logic                             │
  │  If novel math → add isolated function to strategy_backtest/library.py│
  │                  (do NOT write BaseStrategy — developer's job)      │
  │  Create Candidate Card in factor_library/{FactorClass}/             │
  │    • coins: (from 5 supported only)                                 │
  │    • timeframes: (from 5 TFs only)                                  │
  │    • Minimum history: per card                                      │
  │  Write hypothesis report to alpha_forge_v2/hypho_report/            │
  │  Sync Obsidian Ledger                                               │
  │  Send NEW_FACTOR_DISCOVERED to @alpha-developer inbox               │
  │                                                                     │
  │  INBOX PROCESSING (Every run, Model: flash, Cooldown: 5m):          │
  │    DATA_REPAIRED → unblock BLOCKED cards                            │
  │    FINETUNE_PROMOTED → cross-fertilize, look for variants           │
  │    FACTOR_FAILURE_REPORT → add to poison filter, avoid this class   │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## AGENT 2 — @alpha-developer

**Schedule**: Every 60 min | **8-stage build pipeline**

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [1/8] INGEST — Read and validate the Candidate Card                 │
  │                                                                     │
  │  Extract from card YAML frontmatter:                                │
  │    coins:      primary = first listed coin                          │
  │    timeframes: primary = first listed TF                            │
  │    Minimum history: per card                                        │
  │  Check for NEED: lines in "Data Engineer Request" block             │
  │    → IF NEED: lines present → BLOCKED, do not proceed              │
  │  Map available library.py functions to the strategy's requirements  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [2/8] BUILD — Write strategy.py                                     │
  │                                                                     │
  │  Pre-build checklist:                                               │
  │    grep "^def " library.py  → see all 43 available functions        │
  │    skim 1–2 similar existing strategies in strategies/              │
  │                                                                     │
  │  BaseStrategy contract:                                             │
  │    super().__init__(df, **kwargs)  → auto-assigns all kwargs         │
  │    SIGNAL_PARAMS frozenset         → params that affect signals      │
  │    OPTIMIZATION_RANGES dict        → Optuna search space            │
  │    validate_params(cls, params)    → skip invalid combos            │
  │    generate_signals()  → must assign self.df before returning       │
  │    manage_trade()      → returns only engine actions (see Key Rules) │
  │    NO check_regime() method        → use inline boolean mask columns │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [3/7] SYNTAX — AST validation (Model: gemini-2.5-flash)             │
  │                                                                     │
  │  python -c "import ast; ast.parse(open('strategy.py').read())"      │
  │  Fix all import errors and syntax issues before continuing          │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [4/7] SMOKE — Signal sanity and engine action check (Model: flash)  │
  │                                                                     │
  │  ① Call generate_signals() on 1 month of data                       │
  │      (signal==1).sum() > 0  AND  (signal==-1).sum() > 0            │
  │      → BOTH zero = impossible condition, fix before engine          │
  │  ② 1-day backtest to confirm engine runs without crash              │
  │  ③ Verify manage_trade() returns ONLY valid engine actions:         │
  │      SL · TP · TS · EXIT · REVERSE · HOLD · SKIP · ADD             │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [5/7] DEV_REPORT — Backtest, finetune, cross-asset                  │
  │                                                                     │
  │  Date ranges by primary TF:                                         │
  │    5m  → date_from 2025-05-31 │ 15m → date_from 2024-05-31         │
  │    1h  → date_from 2023-05-31 │ 4h  → date_from 2023-05-31         │
  │    1d  → date_from 2022-05-31 │ date_to always 2026-05-31          │
  │                                                                     │
  │  ① Baseline backtest (default params, primary coin/TF)             │
  │  ② Register in settings.py NOW (with default params as placeholder) │
  │  ③ Run finetune.py (Optuna, 100+ trials, multi-objective):          │
  │      python .gemini/skills/crypto-strategy-tuner/scripts/           │
  │             finetune.py --strategy_id {id}                          │
  │      → auto-updates settings.py with Optuna best params             │
  │      → even if strategy is mediocre, keep best params for rescue    │
  │  ④ Final backtest with Optuna best params                           │
  │  ⑤ Cross-asset: SAME TF, other coins listed on card                 │
  │  ⑥ Write dev report with finetuned metrics                         │
  │                                                                     │
  │  Validation tools (manual, dev use):                                │
  │    wfo_runner.py  → 8-fold anchored WFO, WF efficiency + MDD ratio │
  │    validator.py   → full 26-rule Rulebook (T0→T1→T2→T3→CR, /100)   │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [6/7] WFO_EVO — Walk-Forward stability check                        │
  │                                                                     │
  │  4 sliding windows across the date range                            │
  │  Tests stability of OPTIMIZED params (Optuna best from Stage 5)     │
  │  WFO does NOT run Optuna — it tests stability only                  │
  │  FAIL → AUTOPSY (see below)                                         │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [7/7] PBO_AUDIT_&_MANIFEST (Model: gemini-2.5-flash)                │
  │                                                                     │
  │  CPCV (Combinatorial Purged Cross-Validation)                       │
  │  Threshold: PBO < 0.40 = genuine edge                               │
  │  FAIL → AUTOPSY + card status: REJECTED                             │
  │                                                                     │
  │  Verify settings.py has Optuna best params from Stage 5             │
  │    → do NOT overwrite with WFO window-specific params               │
  │  Sync metrics to Obsidian via sync_backtest_to_obsidian.py          │
  │  Append Implementation Metadata Block to Candidate Card             │
  │  Send STRATEGY_READY to @crypto-strategy-tuner inbox                │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ [!] ON_FAIL (any stage) — AUTOPSY                                   │
  │                                                                     │
  │  Write autopsy_report/{date}_{id}_{class}_autopsy.md               │
  │  Document: what failed, why, what was attempted                     │
  │  Card status → REJECTED                                             │
  │  KEEP the settings.py entry — do NOT remove it                      │
  │    → Tuner can still rescue via finetune.py                         │
  │  Run scan_all.py + classify_strategies.py so strategy appears       │
  │    in the backtest dashboard (not invisible):                        │
  │    python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py  │
  │    python .gemini/skills/crypto-strategy-tuner/scripts/classify_strategies.py │
  │  Notify @crypto-strategy-tuner with FACTOR_FAILURE_REPORT           │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## AGENT 3 — @crypto-strategy-tuner

**Schedule**: Every 5 min | **4-stage grader + optimizer**

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [1/4] AUDIT — Load current state                                    │
  │                                                                     │
  │  Load scan_results.json → classify all PENDING strategies           │
  │  Check inbox: STRATEGY_READY from @alpha-developer                  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [2/4] WORK_CYCLE — Scan, tune, rescue                               │
  │                                                                     │
  │  scan_all.py          → full sweep, grade all 119 strategies        │
  │  finetune.py          → Optuna auto-tune (1 auto-tune per wake-up)  │
  │                         scoring: Sharpe 70% + Recovery Factor 30%   │
  │                                  + consistency bonus                │
  │                         auto-expand: if best param hits boundary    │
  │                                      expand range 50%, re-run 75 tr │
  │  find_worst_strategy.py → proactive rescue of bottom-ranked strats  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [3/4] REPORTING — Grade and document                                │
  │                                                                     │
  │  Write backtest report per strategy                                 │
  │  Grade thresholds:                                                  │
  │    🟢 GOOD      Sharpe ≥ 1.0  →  ready for paper trading            │
  │    🟡 MEDIOCRE  Sharpe 0.3–1.0 → worth tuning                       │
  │    🔴 BAD       Sharpe < 0.3  → no edge / proactive finetune        │
  │                                                                     │
  │  IF factor class has ≥ 3 strategies graded BAD or MEDIOCRE          │
  │    with high parameter fragility:                                   │
  │    → send FACTOR_FAILURE_REPORT to @alpha-researcher inbox          │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [4/4] MANIFEST — Promote GOOD strategies                            │
  │                                                                     │
  │  GOOD strategy → write elite report + Market Fit Memo               │
  │               → update settings.py status to PAPER                 │
  │               → sync Obsidian                                       │
  │               → send FINETUNE_PROMOTED to @alpha-researcher inbox   │
  │               → send STRATEGY_VALIDATED to @crypto-fullstack inbox  │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## AGENT 4 — @crypto-data-engineer

**Schedule**: Every 60 min | **4-stage proactive** + reactive on DATA_REQUEST

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  PROACTIVE PIPELINE (every 60 min)                                  │
  │                                                                     │
  │  [1/4] SCAN    — Audit integrity + freshness of parquets            │
  │                  health_scout_v2.py on all 5 coins × 5 TFs          │
  │                  + funding_rate.parquet (all 5 coins, 4h only)      │
  │                                                                     │
  │  [2/4] ANALYZE — Identify gap patterns, schema/dtype errors         │
  │                  Compare known_data_gaps.md vs. actual state        │
  │                                                                     │
  │  [3/4] REPAIR  — Execute sync_all.py or repair_dtypes.py            │
  │                  incremental_fetcher.py for missing periods         │
  │                  vpn_manager.py if Binance rate-limited             │
  │                  Always create .bak snapshot before repair          │
  │                                                                     │
  │  [4/4] VERIFY  — Final integrity check                              │
  │                  Update known_data_gaps.md (add/remove entries)     │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │ (also runs reactively)
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  REACTIVE PIPELINE (triggered by DATA_REQUEST inbox message)        │
  │                                                                     │
  │  Received from: @alpha-researcher or @alpha-developer               │
  │  Message contains: NEED: lines from Candidate Card                  │
  │                                                                     │
  │  [1] Assess the NEED: lines — what data type is required?           │
  │      • Open Interest  → fetch from Binance futures API              │
  │      • Liquidation events → fetch from Coinglass or Binance         │
  │      • Order book depth → snapshot API                              │
  │      • Long/Short ratio → funding API extension                     │
  │  [2] Fetch + validate the data                                      │
  │  [3] Store in dataset/{COIN}/{TF}/{metric}.parquet                  │
  │  [4] Run repair_dtypes.py on new file                               │
  │  [5] Reply to sender inbox with DATA_VALIDATION_DONE                │
  │      → include: parquet path, columns available, date range         │
  │  [6] Update known_data_gaps.md                                      │
  └─────────────────────────────────────────────────────────────────────┘

  Data Universe managed:
  5 coins: BTC · ETH · BNB · SOL · XRP
  5 TFs:   5m  · 15m  · 1h  · 4h  · 1d
  Funding rate: 4h only, all 5 coins
```

---

## AGENT 5 — @crypto-qa-tester

**Schedule**: Every 60 min | **5-stage test suite + routing**

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [1/5] GROUP_1 — Flask API Route Validation                          │
  │                                                                     │
  │  Run system_test.py --group 1                                       │
  │  Test all Flask endpoints: /api/scan_summary · /api/strategies ·   │
  │                             /api/backtest · /api/logs · etc.        │
  │  FAIL → retry once (flaky test rule)                                │
  │  FAIL after retry → route to @crypto-fullstack inbox                │
  │    Message: FLASK_ROUTE_FAIL with endpoint, error, traceback         │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [2/5] GROUP_2 — Strategy Import & Engine Integrity                  │
  │                                                                     │
  │  Import all strategy classes in strategies/                         │
  │  Verify BaseStrategy subclass contract                              │
  │  Run 1-bar smoke test on each                                       │
  │  FAIL → retry once                                                  │
  │  FAIL after retry → route to @alpha-developer inbox                 │
  │    (or @crypto-fullstack if import error is infrastructure-level)    │
  │    Message: STRATEGY_IMPORT_FAIL with class, error, traceback        │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [3/5] GROUP_3 — Data Linkage & Smoke Simulation                     │
  │                                                                     │
  │  Verify parquet paths match settings.py coin/TF config              │
  │  Check column schema in parquets                                    │
  │  Run end-to-end smoke backtest on 1 strategy × 1 day               │
  │  FAIL → retry once                                                  │
  │  FAIL after retry → route to @crypto-data-engineer inbox            │
  │    Message: DATA_LINKAGE_FAIL with parquet path, missing columns    │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [4/5] GROUP_5 — Registration Audit                                  │
  │                                                                     │
  │  Run check_registration.py to find strategy .py files with no       │
  │  matching entry in settings.py (invisible to pipeline)              │
  │  FAIL (unregistered classes found) → route to @alpha-developer      │
  │    Message: STRATEGY_IMPORT_FAIL listing unregistered class names   │
  │                                                                     │
  │  Cross-check settings.py IDs vs scan_results.json IDs              │
  │  Any ID in settings.py missing from scan_results.json →            │
  │    route to @crypto-strategy-tuner to trigger scan                  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [5/5] FINALIZE — Activity log + route unhandled failures            │
  │                                                                     │
  │  Append to activity log: all pass/fail with timestamps              │
  │  Format: [YYYY-MM-DD HH:MM] {ACTION} | {Target} | {Details}        │
  │  Actions: ▶ START · ⚙ WORK · ✓ RESULT · ⚠ WARN · ✗ FAIL · 🏁 FINISH│
  │  Append summary to .gemini/shared/AGENT_COLLABORATION.md            │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## AGENT 6 — @crypto-fullstack

**Schedule**: Every 30 min | **4-stage infra repair**

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [1/4] TRIAGE — Read logs and bug patterns                           │
  │                                                                     │
  │  Read in order:                                                     │
  │    references/bug_patterns.md    (FIRST — known root causes + fixes)│
  │    server.log                    (Flask tracebacks)                 │
  │    error_log.jsonl               (structured error events)          │
  │  Check inbox for routed failures:                                   │
  │    FLASK_ROUTE_FAIL from @crypto-qa-tester                          │
  │    STRATEGY_VALIDATED from @crypto-strategy-tuner                   │
  │    Any infra-level STRATEGY_IMPORT_FAIL from @crypto-qa-tester      │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [2/4] IMPLEMENT — Patch the identified issue                        │
  │                                                                     │
  │  Patch scope: main.py · monitor_app.js · index.html ·               │
  │               phase_6_agent_monitor/ · main_controller/             │
  │  Fix Flask route errors, missing endpoints, broken UI               │
  │  Wire new validated strategies to paper trading dashboard           │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [3/4] CHAOS_TEST — Verify after every patch                         │
  │                                                                     │
  │  Run chaos_test.py against all Flask routes                         │
  │  Confirm no regressions introduced                                  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ [4/4] FINALIZE — Sync knowledge base                                │
  │                                                                     │
  │  Run sync_knowledge_base.py (MANDATORY every session)               │
  │    → regenerates .gemini/shared/KNOWLEDGE_BASE.md                  │
  │    → pulls from scan_results.json + settings.py                    │
  │  Notify relevant agents if patch resolves their reported failure    │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## INTER-AGENT COMMUNICATION SCENARIOS

### SCENARIO A — Researcher discovers strategy, needs new data type

Trigger: @alpha-researcher finds an Open Interest-based strategy. OI is not in existing parquets.

```
  @alpha-researcher
      │
      │  [2/4] EXTRACT_ALPHA: OI not in data universe columns
      │         → fills "Data Engineer Request" block in card:
      │           NEED: open_interest (BTC, 1h, 2023-05-31 to 2026-05-31)
      │         → sets card status: BLOCKED
      │
      ├──── writes to inbox: .gemini/skills/crypto-data-engineer/inbox/
      │     {
      │       "topic":   "DATA_REQUEST",
      │       "from":    "alpha-researcher",
      │       "card":    "factor_library/Sentiment_OnChain/OI_Divergence_BTC_1h.md",
      │       "need":    "NEED: open_interest (BTC, 1h, 2023-05-31 to 2026-05-31)"
      │     }
      │
      ▼ (researcher continues with other QUEUED cards, does not block)
  
  @crypto-data-engineer  (next session, reads inbox)
      │
      │  [1/4] SCAN: receives DATA_REQUEST
      │  [2/4] ANALYZE: identifies OI endpoint on Binance futures API
      │  [3/4] REPAIR:
      │         → fetch open_interest data from Binance futures
      │         → store at dataset/BTC/1h/open_interest.parquet
      │         → run repair_dtypes.py on new file
      │  [4/4] VERIFY: confirm date range, columns, no dtype errors
      │
      ├──── writes to inbox: .gemini/skills/alpha-researcher/inbox/
      │     {
      │       "topic":  "DATA_VALIDATION_DONE",
      │       "from":   "crypto-data-engineer",
      │       "card":   "factor_library/Sentiment_OnChain/OI_Divergence_BTC_1h.md",
      │       "data":   "dataset/BTC/1h/open_interest.parquet — col: open_interest",
      │       "range":  "2023-05-31 to 2026-05-31"
      │     }
      │
      ▼
  
  @alpha-researcher  (next session, reads inbox)
      │
      │  Receives DATA_VALIDATION_DONE
      │  Removes NEED: lines from card
      │  Updates card status: BLOCKED → QUEUED
      │  Sends NEW_FACTOR_DISCOVERED to @alpha-developer inbox
      │
      ▼
  
  @alpha-developer  picks up QUEUED card next cycle → normal 8-stage build
```

---

### SCENARIO B — Normal research → developer flow (no data gap)

Trigger: @alpha-researcher finds a standard RSI divergence strategy using only OHLCV.

```
  @alpha-researcher
      │
      │  [1/4] WEB_SEARCH: finds RSI divergence strategy on GitHub
      │  [2/4] EXTRACT_ALPHA:
      │         → coins: BTC (primary), ETH — both in data universe ✅
      │         → timeframe: 1h — in data universe ✅
      │         → columns: RSI (derivable from Close) ✅
      │         → DECISION: status QUEUED, no data request needed
      │  [3/4] HYPHO_REPORT:
      │         → creates hypothesis report
      │         → adds calc_rsi_divergence() to library.py
      │         → creates card at factor_library/Mean_Reversion/
      │           RSI_Divergence_BTC_1h.md
      │  [4/4] INDEX_SYNC:
      │         → writes to inbox: .gemini/skills/alpha-developer/inbox/
      │           { "topic": "NEW_FACTOR_DISCOVERED",
      │             "card":  "factor_library/Mean_Reversion/RSI_Divergence_BTC_1h.md",
      │             "fn":    "calc_rsi_divergence" }
      │         → sets card status: HANDED_OFF
      │
      ▼
  
  @alpha-developer  (next session, reads inbox)
      │
      │  Receives NEW_FACTOR_DISCOVERED
      │  Begins 8-stage pipeline on RSI_Divergence_BTC_1h.md
      │  ... (see Agent 2 stages above)
      │
      ▼
  
  [8/8] MANIFEST → sends STRATEGY_READY to @crypto-strategy-tuner inbox
```

---

### SCENARIO C — Developer → Tuner handoff

Trigger: @alpha-developer completes [8/8] MANIFEST for a new strategy.

```
  @alpha-developer
      │
      │  [8/8] MANIFEST:
      │         → settings.py updated with Optuna best params
      │         → writes to inbox: .gemini/skills/crypto-strategy-tuner/inbox/
      │           {
      │             "topic":      "STRATEGY_READY",
      │             "from":       "alpha-developer",
      │             "strategy_id": "rsi_divergence_btc_1h",
      │             "class":       "RSIDivergence",
      │             "card":        "factor_library/Mean_Reversion/..."
      │           }
      │
      ▼
  
  @crypto-strategy-tuner  (next 5-min cycle, reads inbox)
      │
      │  [1/4] AUDIT: receives STRATEGY_READY, adds to scan queue
      │  [2/4] WORK_CYCLE:
      │         → scan_all.py includes new strategy
      │         → finetune.py auto-tune scheduled
      │  [3/4] REPORTING: grades new strategy
      │         Sharpe ≥ 1.0 → GOOD
      │         Sharpe 0.3–1.0 → MEDIOCRE
      │         Sharpe < 0.3 → BAD
      │  [4/4] MANIFEST (if GOOD):
      │         → writes elite report
      │         → settings.py status → PAPER
      │         → sends FINETUNE_PROMOTED to @alpha-researcher inbox
      │         → sends STRATEGY_VALIDATED to @crypto-fullstack inbox
```

---

### SCENARIO D — Tuner finds persistent BAD → Poison filter

Trigger: After 3 finetune attempts, Ichimoku-based strategy class still Sharpe < 0.3.

```
  @crypto-strategy-tuner
      │
      │  [3/4] REPORTING: detects Ichimoku factor class:
      │         4 out of 5 strategies: BAD, avg Sharpe 0.12
      │         High parameter fragility across all 4
      │
      │  [4/4] MANIFEST:
      │         → writes to autopsy_report/ for affected strategies
      │         → writes to inbox: .gemini/skills/alpha-researcher/inbox/
      │           {
      │             "topic":    "FACTOR_FAILURE_REPORT",
      │             "from":     "crypto-strategy-tuner",
      │             "class":    "Ichimoku",
      │             "detail":   "4/5 strategies BAD, avg Sharpe 0.12 across
      │                          BTC/ETH/1h/4h. Avoid proposing Ichimoku-based
      │                          factors until structural fix identified.",
      │             "strategies": ["ichimoku_btc_1h", "ichimoku_eth_4h", ...]
      │           }
      │
      ▼
  
  @alpha-researcher  (next session, reads inbox)
      │
      │  Receives FACTOR_FAILURE_REPORT
      │  Adds Ichimoku to internal poison filter awareness
      │  Future WEB_SEARCH / EXTRACT_ALPHA:
      │    → deprioritizes Ichimoku-based ideas
      │    → notes in hypothesis reports: "prior failure class — avoid unless
      │       structural change identified"
```

---

### SCENARIO E — QA finds broken Flask route → routes to Fullstack

```
  @crypto-qa-tester
      │
      │  [1/4] GROUP_1: POST /api/run_backtest returns 500
      │         Retry → still 500
      │
      │  Route to @crypto-fullstack inbox:
      │    {
      │      "topic":     "FLASK_ROUTE_FAIL",
      │      "from":      "crypto-qa-tester",
      │      "endpoint":  "POST /api/run_backtest",
      │      "status":    500,
      │      "traceback": "KeyError: 'strategy_id' in main.py:284"
      │    }
      │
      ▼
  
  @crypto-fullstack
      │
      │  [1/4] TRIAGE: reads FLASK_ROUTE_FAIL inbox, checks bug_patterns.md
      │         → finds matching pattern: missing param validation
      │  [2/4] IMPLEMENT: patches main.py:284
      │  [3/4] CHAOS_TEST: re-runs chaos_test.py → all routes pass
      │  [4/4] FINALIZE: runs sync_knowledge_base.py
      │         → notifies @crypto-qa-tester: PATCH_APPLIED
```

---

### SCENARIO F — QA finds broken strategy import → routes to Developer

```
  @crypto-qa-tester
      │
      │  [2/4] GROUP_2: ImportError on strategies/ichimoku_v2.py
      │         Retry → still fails
      │
      │  Route to @alpha-developer inbox:
      │    {
      │      "topic":     "STRATEGY_IMPORT_FAIL",
      │      "from":      "crypto-qa-tester",
      │      "file":      "strategies/ichimoku_v2.py",
      │      "error":     "ImportError: cannot import name 'calc_ichimoku_cloud'
      │                    from library — function renamed or removed"
      │    }
      │
      ▼
  
  @alpha-developer
      │
      │  Receives STRATEGY_IMPORT_FAIL
      │  Checks library.py for current function name
      │  Patches import in ichimoku_v2.py
      │  Re-runs [3/8] SYNTAX + [4/8] SMOKE to confirm fix
```

---

### SCENARIO G — QA finds data linkage issue → routes to Data Engineer

```
  @crypto-qa-tester
      │
      │  [3/4] GROUP_3: smoke backtest fails — parquet missing 'num_trades' col
      │         in dataset/SOL/15m/spot_ohlcv.parquet
      │         Retry → still fails
      │
      │  Route to @crypto-data-engineer inbox:
      │    {
      │      "topic":    "DATA_LINKAGE_FAIL",
      │      "from":     "crypto-qa-tester",
      │      "parquet":  "dataset/SOL/15m/spot_ohlcv.parquet",
      │      "missing":  "column 'num_trades' not found",
      │      "expected": "Open High Low Close Volume taker_buy_base_vol num_trades"
      │    }
      │
      ▼
  
  @crypto-data-engineer
      │
      │  Receives DATA_LINKAGE_FAIL
      │  [3/4] REPAIR: re-fetches SOL/15m from Binance,
      │                ensures num_trades column present
      │                runs repair_dtypes.py
      │  [4/4] VERIFY: confirms schema matches expected
      │         → notifies @crypto-qa-tester: DATA_REPAIRED
      │         → updates known_data_gaps.md
```

---

## CANDIDATE CARD STATUS LIFECYCLE

```
  Created by @alpha-researcher
          │
          ▼
      ┌─────────┐
      │  QUEUED │ ◄────────────────────────────────────────────────────┐
      └────┬────┘   (DATA_VALIDATION_DONE received from data engineer) │
           │                                                           │
           │  needs OI / liquidations / order book data               │
           ├──────────────────────────────────────────────────────────►│
           │  fills Data Engineer Request block                        │
           │  sends DATA_REQUEST inbox message                         │
           │                                                           │
           ▼                                                     ┌─────┴───────┐
      ┌────────────────┐                                         │   BLOCKED   │
      │  HANDED_OFF    │ ◄── researcher sends NEW_FACTOR_DISCOVERED              │
      └──────┬─────────┘    and updates card status             └─────────────┘
             │
             │  @alpha-developer picks card from inbox (FIFO) or
             │  scans factor_library/ for QUEUED cards (interest: High first)
             ▼
      ┌─────────────────┐
      │   IN_PROGRESS   │  (developer is actively building this card)
      └──────┬──────────┘
             │
             ├─── ALL 8 stages PASS ─────────────────────────────────────────┐
             │                                                                │
             └─── ANY stage FAIL ──► ┌───────────┐                          │
                                      │ REJECTED  │ ◄── autopsy_report/ written│
                                      │           │     card not deleted       │
                                      └───────────┘     settings.py entry kept │
                                                         id gets _REJECTED suffix│
                                                                                ▼
                                                                       ┌──────────────┐
                                                                       │  VALIDATED   │
                                                                       │  (PAPER_READY│
                                                                       │  elite report│
                                                                       │  written)    │
                                                                       └──────────────┘

  Valid transitions:
  QUEUED      → BLOCKED      (NEED: lines found, DATA_REQUEST sent)
  BLOCKED     → QUEUED       (DATA_VALIDATION_DONE received)
  QUEUED      → HANDED_OFF   (researcher sends NEW_FACTOR_DISCOVERED)
  HANDED_OFF  → IN_PROGRESS  (developer picks up the card)
  IN_PROGRESS → REJECTED     (any stage fails)
  IN_PROGRESS → VALIDATED    (all 8 stages pass, Tuner grades GOOD)

  Notes:
  • REJECTED cards remain in factor_library/ and settings.py — they are NOT deleted
  • The Tuner can still rescue a REJECTED strategy via finetune.py
  • A card can stay BLOCKED indefinitely if data engineer cannot fulfil the request
  • Researcher does NOT wait for BLOCKED cards — continues with other QUEUED cards
```

---

## SHARED MEMORY ARCHITECTURE

All 6 agents persist knowledge across sessions using a 3-tier memory system. No agent starts each session with a blank slate.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  TIER 1 — Agent-Local LTM  (per-agent, written by that agent only)  │
  │                                                                     │
  │  Location: .gemini/skills/{agent}/LTM.md                           │
  │  Format:   [YYYY-MM-DD] | {PATTERN} | {CONSTRAINT}                 │
  │                                                                     │
  │  Contains: agent-specific wins, failures, discovered patterns,      │
  │            parameter insights, strategy-class observations          │
  │  Read by:  that agent only, at start of every session               │
  │  Written:  immediately when a new pattern or constraint is learned  │
  │                                                                     │
  │  Example (researcher LTM.md):                                       │
  │    [2026-06-10] | Volatility squeeze → breakout confirmed by        │
  │                   volume + RSI shows promise for ETH                │
  └─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ cross-agent insights escalated here
                                   ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  TIER 2 — System-Wide GLOBAL_LTM  (shared, all agents read+write)  │
  │                                                                     │
  │  Location: .gemini/shared/GLOBAL_LTM.md                            │
  │  Format:   [YYYY-MM-DD] | {PATTERN} | {CONSTRAINT}                 │
  │                                                                     │
  │  Contains: architecture decisions, cross-agent bugs, engine rules,  │
  │            data universe constraints, finetune/WFO rules            │
  │            (e.g. "manage_trade must return ONLY these strings...")   │
  │  Read by:  ALL 6 agents at start of every session (Memory Protocol) │
  │  Written:  any agent when pattern affects multiple agents            │
  │                                                                     │
  │  This is the PRIMARY source of shared constraints — agents read     │
  │  this to avoid repeating the same class of mistake across sessions  │
  └─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ machine-generated snapshot
                                   ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  TIER 3 — KNOWLEDGE_BASE.md  (machine-generated, read-only)         │
  │                                                                     │
  │  Location: .gemini/shared/KNOWLEDGE_BASE.md                         │
  │                                                                     │
  │  Generated by: sync_knowledge_base.py (run by @crypto-fullstack     │
  │                at every [4/4] FINALIZE — mandatory)                 │
  │  Sources:      scan_results.json + settings.py                      │
  │  Contains:     current strategy count, grades, registered IDs,      │
  │                live pipeline state — factual snapshot, not opinions │
  │  Read by:      ALL 6 agents to understand current system state      │
  │                without having to parse scan_results.json directly   │
  │                                                                     │
  │  Freshness: as fresh as the last @crypto-fullstack session          │
  │  Warning: do NOT treat KNOWLEDGE_BASE.md as authoritative for       │
  │           grades — scan_results.json is the source of truth         │
  └─────────────────────────────────────────────────────────────────────┘

  Session startup order (all 6 agents):
  1. Read LTM.md (own)
  2. Read GLOBAL_LTM.md (shared)
  3. Read KNOWLEDGE_BASE.md (shared snapshot)
  4. Check own inbox/ for pending messages
  5. Begin pipeline stages
```

---

## MEDIOCRE RESCUE LOOP

```
  Strategy graded MEDIOCRE (Sharpe 0.3 – 1.0) after scan_all.py
          │
          ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  @crypto-strategy-tuner — [2/4] WORK_CYCLE                       │
  │                                                                  │
  │  find_worst_strategy.py selects rescue target:                   │
  │    • Lowest Sharpe in MEDIOCRE pool                              │
  │    • OR highest param fragility (±10% param change crashes Sharpe)│
  │    • 1 auto-tune per wake-up (every 5 min)                       │
  │                                                                  │
  │  finetune.py runs Optuna rescue:                                 │
  │    Scoring: Sharpe 70% + Recovery Factor 30% + consistency bonus │
  │    Trials: 100–400 depending on prior attempt history            │
  │    Auto-expand: if best param hits range boundary                │
  │                 → expand range 50% → re-run 75 more trials       │
  │    Writes best params back to settings.py                        │
  └──────────────────────────────────────────────────────────────────┘
          │
          │  next scan cycle (every 5 min)
          ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  Re-grade after rescue                                           │
  └──────────────────────────────────────────────────────────────────┘
          │
          ├─── Sharpe ≥ 1.0 ──────────────────────────────────────────────────►  PROMOTED
          │                                                                        │
          │    Tuner [4/4] MANIFEST:                                              │
          │      → writes elite_report/ (status: PAPER_READY)                    │
          │      → settings.py id keeps same (no _REJECTED suffix)               │
          │      → FINETUNE_PROMOTED → @alpha-researcher                          │
          │      → STRATEGY_VALIDATED → @crypto-fullstack                         │
          │                                                                        │
          ├─── Still MEDIOCRE ────────────────────────────────────────────────►  STAYS IN POOL
          │                                                                        │
          │    Strategy remains in MEDIOCRE pool                                  │
          │    Eligible for rescue again on future wake-ups                       │
          │    No hard give-up count — rescue is opportunistic                    │
          │                                                                        │
          └─── Still BAD / param fragility persists across factor class ───────►  POISON SIGNAL
                                                                                   │
               If ≥ 3 strategies in same factor class hit this state:             │
                 → FACTOR_FAILURE_REPORT to @alpha-researcher                     │
                 → Researcher adds class to poison filter                         │
                 → GLOBAL_LTM entry added: "Repeated fine-tuning on              │
                   consistently low/negative Sharpe indicates structural          │
                   flaw — redesign, do not keep tuning"                          │

  No hard give-up threshold exists. Rescue is indefinite but opportunistic.
  The GLOBAL_LTM entry is the soft signal to abandon a class.
```

---

## MODEL ALLOCATION PER AGENT

No model is hard-coded in any skill file. The model used is determined by which model the user invokes the agent with at runtime. This matters because model capability directly affects what agents can do.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Agent                   │ Web Search │ Notes                       │
  │  ───────────────────────────────────────────────────────────────    │
  │  @alpha-researcher       │ Required   │ Flash → queue-only fallback │
  │                          │            │ Pro   → full web discovery  │
  │  @alpha-developer        │ Not used   │ any model works             │  │  @crypto-strategy-tuner  │ Not used   │ any model works             │
  │  @crypto-data-engineer   │ Not used   │ any model works             │
  │  @crypto-qa-tester       │ Not used   │ any model works             │
  │  @crypto-fullstack       │ Not used   │ any model works             │
  └─────────────────────────────────────────────────────────────────────┘

  Flash model fallback (only affects @alpha-researcher):
    • [1/4] WEB_SEARCH: google_web_search tool is unavailable
    • Fallback: skip WEB_SEARCH entirely, go directly to [2/4] QUEUE PICKUP
    • Researcher still processes QUEUED cards from factor_library/
    • No new factors discovered from web this session
    • All 4 stages still execute — only channel ① (Web Research) is blocked

  Current model in Phase 6 monitor:
    Each agent terminal card shows a model badge (badge-model) updated in real-time
    via heartbeat.json → monitor reads which model each agent last used
```

---

## QUEUED CARD PRIORITY ORDER

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  @alpha-researcher — Queue Pickup priority ([1/4] WEB_SEARCH → skip)│
  │                                                                     │
  │  Priority order when scanning factor_library/ for QUEUED cards:    │
  │    1st  interest: High   (researcher-assigned on card creation)     │
  │    2nd  interest: Medium                                            │
  │    3rd  interest: Low                                               │
  │    Tie-break: older card first (FIFO within same interest level)    │
  │                                                                     │
  │  Interest levels are set by @alpha-researcher at card creation      │
  │  based on: novelty of the alpha factor, data availability,          │
  │  confidence in the mathematical edge                                 │
  └─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │  NEW_FACTOR_DISCOVERED message
                                   ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  @alpha-developer — Card selection priority                          │
  │                                                                     │
  │  Step 1: Check inbox/ for NEW_FACTOR_DISCOVERED messages first      │
  │          Process in FIFO order (oldest message first)               │
  │                                                                     │
  │  Step 2: If inbox is empty, scan factor_library/ directly:          │
  │          Pick QUEUED cards by interest: High → Medium → Low         │
  │          (same ordering as researcher queue pickup)                 │
  │                                                                     │
  │  Step 3: One card per session cycle (60 min window)                 │
  │          Developer does NOT start a second card in the same session │
  │          if the first card reaches Stage 5+ (expensive compute)     │
  │                                                                     │
  │  BLOCKED cards are invisible to the developer — they do NOT appear  │
  │  in the build queue even if interest: High                          │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## STRATEGY GRADE & STATUS TRACKING

Settings.py does NOT have a `status` or `grade` field. Grade and deployment status are tracked across three separate locations:

```
  settings.py  (params + metadata only — no grade, no status)
  ─────────────────────────────────────────────────────────────
  "42": {
    "id":     "RSI_DIVERGENCE_BTC_1H",          ← normal strategy
    "id":     "RSI_MR_BTC_1H_REJECTED",         ← rejected: _REJECTED suffix in id
    "class":  "RSIDivergence",
    "data":   { "coins": "BTC", "timeframes": "1h", ... },
    "params": { ... }                            ← always Optuna best (from finetune.py)
  }
  • Entry is NEVER deleted — even REJECTED strategies stay in settings.py
  • Tuner can still rescue a REJECTED strategy via finetune.py
  • _REJECTED suffix is a naming convention only, not a machine-readable field

  ─────────────────────────────────────────────────────────────────────
  scan_results.json  (authoritative grade source — updated each scan)
  ─────────────────────────────────────────────────────────────────────
  "results": {
    "42": {
      "sharpe":       1.23,
      "grade":        "GOOD",       ← GOOD | MEDIOCRE | BAD
      "grade_reason": "...",
      ...
    }
  }
  Top-level: { "GOOD": 7, "MEDIOCRE": 44, "BAD": 59, "PENDING": N, "ERROR": N }
  Regenerated by scan_all.py on every tuner WORK_CYCLE

  ─────────────────────────────────────────────────────────────────────
  elite_report/  (PAPER_READY flag — written only for GOOD strategies)
  ─────────────────────────────────────────────────────────────────────
  phase_6_agent_monitor/alpha_forge_v2/elite_report/
    {strategy_id}_{class}_elite.md
    YAML frontmatter: { status: PAPER_READY }

  ─────────────────────────────────────────────────────────────────────
  Grade lifecycle for a strategy:
  ─────────────────────────────────────────────────────────────────────

  Registered in settings.py (Stage 5)
          │
          ▼
  scan_results.json: PENDING
          │
          │  scan_all.py runs
          ▼
  scan_results.json: GOOD / MEDIOCRE / BAD
          │
          ├── GOOD ────► elite_report/ created (status: PAPER_READY)
          │              → paper trading monitoring begins
          │
          ├── MEDIOCRE ► finetune.py rescue cycles indefinitely
          │              → re-graded each scan
          │
          └── BAD ──────► finetune.py rescue (proactive, find_worst_strategy.py)
                          → still BAD after class-level pattern: autopsy_report/
                             settings.py entry gets _REJECTED suffix in id
                             FACTOR_FAILURE_REPORT → researcher
```

---

## MESSAGE TYPES REFERENCE

| Message Topic | From | To | Trigger |
|---|---|---|---|
| `NEW_FACTOR_DISCOVERED` | @alpha-researcher | @alpha-developer | New card written, status HANDED_OFF |
| `DATA_REQUEST` | @alpha-researcher | @crypto-data-engineer | Card has NEED: lines, status BLOCKED |
| `DATA_VALIDATION_DONE` | @crypto-data-engineer | @alpha-researcher | New data fetched and validated |
| `DATA_REPAIRED` | @crypto-data-engineer | @alpha-researcher / @crypto-qa-tester | Gap filled or dtype fixed |
| `STRATEGY_READY` | @alpha-developer | @crypto-strategy-tuner | Stage 8 MANIFEST complete |
| `FINETUNE_PROMOTED` | @crypto-strategy-tuner | @alpha-researcher | Strategy graded GOOD |
| `STRATEGY_VALIDATED` | @crypto-strategy-tuner | @crypto-fullstack | GOOD strategy needs paper trading wiring |
| `FACTOR_FAILURE_REPORT` | @crypto-strategy-tuner | @alpha-researcher | Factor class ≥ 3 BAD strategies |
| `FLASK_ROUTE_FAIL` | @crypto-qa-tester | @crypto-fullstack | Flask API test fails after retry |
| `STRATEGY_IMPORT_FAIL` | @crypto-qa-tester | @alpha-developer | Strategy import fails after retry |
| `DATA_LINKAGE_FAIL` | @crypto-qa-tester | @crypto-data-engineer | Data linkage smoke test fails |
| `PATCH_APPLIED` | @crypto-fullstack | @crypto-qa-tester | Bug fixed, requesting retest |

---

## LIVE SNAPSHOT (2026-06-18)

| Metric | Count |
|---|---|
| Strategies in settings.py | **119** |
| Strategy .py files | 74 |
| Dev reports written | 28 |
| Autopsy reports | 2 |
| Candidate Cards in factor_library/ | 112 |
| Cards QUEUED (awaiting build) | 37 |
| Cards VALIDATED | 2 |
| library.py functions | 43 |
| Hypothesis reports | 35 |
| 🟢 GOOD strategies (Sharpe ≥ 1.0) | **7** |
| 🟡 MEDIOCRE (Sharpe 0.3–1.0) | **44** |
| 🔴 BAD (Sharpe < 0.3) | **59** |
| Last full scan | 2026-06-17 |

---

## KEY RULES (hard constraints)

| Rule | Constraint |
|---|---|
| Supported coins | BTC · ETH · BNB · SOL · XRP only |
| Available timeframes | 5m · 15m · 1h · 4h · 1d only |
| known_data_gaps.md | Logs partial gaps only — does NOT mean coin/TF is unusable |
| finetune before WFO | Stage 5 runs Optuna BEFORE Stage 6 WFO |
| WFO ≠ best params | WFO tests stability only — never overwrite Optuna params |
| manage_trade actions | SL · TP · TS · EXIT · REVERSE · HOLD · SKIP · ADD only |
| Exit modes | FIXED_RR · TRAILING_STOP only (not FIXED_TP) |
| settings.py registration | Mandatory at Stage 5, before WFO/PBO |
| check_regime() | Does NOT exist in BaseStrategy — use inline boolean masks |
| State reset | Track entry_price to detect new trades and reset SL/TP/TS |
| Signal sanity | Count signals before engine — 0 signals = impossible condition |
| BLOCKED card rule | Developer does NOT start card if NEED: lines are present |
| Flaky test rule | QA retries once before routing to other agents |
| DATA_REQUEST flow | Researcher marks card BLOCKED, sends DATA_REQUEST, continues with other cards |
