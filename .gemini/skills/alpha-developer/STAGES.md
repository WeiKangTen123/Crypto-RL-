# ALPHA DEVELOPER: STAGE-SPECIFIC MISSIONS

## STAGE 1: INGEST
- **Goal**: Load Alpha Card & Math building blocks.
- **Instruction**:
    1. Read the Candidate Card in `factor_library/`. Map the mathematical core. Verify required `library.py` functions exist.
    2. **Extract and record these fields from the card's YAML frontmatter** — they drive all backtest config decisions in Stage 5:
       - `coins` → primary coin = first listed (e.g. `BTC, ETH, SOL` → primary is `BTC`)
       - `timeframes` → primary timeframe = first listed (e.g. `15m, 1h` → primary is `15m`)
       - `type` → short-term / long-term / mean-reversion etc.
    3. From the card body, extract `Minimum history` (e.g. "2 years") — use it to set `date_from` in Stage 5.
    4. Note any `NEED:` lines in "Data Engineer Request" — if present, the card is BLOCKED. Do not proceed until data is available.
- **Mandatory Output**: `[1/8] INGEST: Reading Alpha Card & Mapping Math Factors... Primary: {coin}/{tf}, Min history: {N} years`

## STAGE 2: BUILD
- **Goal**: Strategy code assembly.
- **Pre-Build Checklist (do BEFORE writing code)**:
    1. **Library Inventory**: Run `grep "^def " strategy_backtest/library.py` — do NOT reimplement existing indicators. Available functions: calc_atr, calc_ema, calc_rsi, calc_macd, calc_adx_dmi, calc_bollinger_bands, calc_zscore, calc_vwap, calc_donchian_channels, calc_supertrend, calc_ichimoku, calc_keltner_channels, calc_stoch_kdj, calc_wavetrend, calc_mfi, calc_cci, calc_aroon, calc_tsi, calc_fisher_transform, calc_vrsi, calc_kdj, calc_lorentzian_classification, detect_fvg, detect_swing_high_low, detect_divergence, detect_candle_engulfing, detect_candle_hammer, detect_order_blocks, and more.
    2. **Existing Strategy Scan**: `ls strategy_backtest/strategies/` and skim 1–2 strategies with a similar factor class. Copy their structural pattern — do not invent your own.
- **Instruction**: Write Python code in `strategy_backtest/strategies/`. You MUST include 2–3 **Logic Switches** in an `OPTIMIZATION_RANGES` dictionary.
- **BaseStrategy Contract (must know before coding)**:
    - `super().__init__(df, **kwargs)` auto-assigns ALL kwargs as `self.attr = value` via setattr. Only put params in `__init__` that need explicit type-casting (int/float) — all others are handled automatically.
    - `SIGNAL_PARAMS = frozenset({...})` — declare params that affect signal generation (not risk). The optimizer uses this to determine when to regenerate signals vs. reuse cached ones.
    - Override `validate_params(cls, params)` to enforce optimizer constraints (e.g. `fast_period < slow_period`). Return False to skip invalid combos.
    - `generate_signals()` MUST assign `self.df = df` before returning the updated `df` with a `'signal'` column (1=long, -1=short, 0=flat).
- **Regime Filtering**: There is NO `check_regime()` method in BaseStrategy. Implement regime guards inline in `generate_signals()` as boolean mask columns (e.g. `trend_up = df['Close'] > ema_200`) and AND them with signal conditions. See existing strategies for examples.
- **Mandatory Output**: `[2/8] BUILD: Assembling Strategy Logic (Signals & Logic Switches)...`

## STAGE 3: SYNTAX
- **Goal**: Static analysis.
- **Instruction**: Run Python AST check and integrity validation. Fix syntax/import errors immediately in the strategy file.
- **Mandatory Output**: `[3/8] SYNTAX: Running Python AST check & Integrity Validation...`

## STAGE 4: SMOKE
- **Goal**: Execution check.
- **Instruction**:
    1. **Signal Sanity Check FIRST** — before running the engine, call `strategy.generate_signals()` on 1 month of data and print the long/short signal counts. If both are 0, your signal condition is mathematically impossible on this data — fix it before proceeding. See `references/templates.md` Signal Sanity Check section for common causes and fixes.
    2. Run a quick 1-day backtest using `run_backtest.py`. If zero trades → diagnose using the signal count above, fix logic, and re-run.
    3. Verify `manage_trade` returns only engine-recognized actions: `'SL'`, `'TP'`, `'TS'`, `'EXIT'`, `'REVERSE'`, `'HOLD'`, `'SKIP'`, `'ADD'`. Any other string is silently ignored and leaves the position open forever.
- **Mandatory Output**: `[4/8] SMOKE: Signal count check + 1-day trade execution simulation...`

## STAGE 5: DEV_REPORT
- **Goal**: Baseline → Optuna optimization → register best params → write dev report.
- **Why finetune first**: WFO/PBO (Stages 6–7) must test the *optimized* strategy, not defaults. A good strategy can fail WFO on poor default params. Running finetune here ensures WFO tests the best possible version.
- **Instruction**:
    1. **Determine coin, timeframe, and date range from the Candidate Card** (extracted in Stage 1):
       - Primary coin = first listed in card's `coins` field
       - Primary timeframe = first listed in card's `timeframes` field
       - `date_to` is always `2026-05-31` (data cutoff)
       - `date_from` based on timeframe (see table in `references/templates.md` → Timeframe Config Table):
         - 5m  → 2025-05-31  (1 year)
         - 15m → 2024-05-31  (2 years)
         - 1h  → 2023-05-31  (3 years)
         - 4h  → 2023-05-31  (3 years)
         - 1d  → 2022-05-31  (4 years)
         - If card specifies "Minimum history: N years", use whichever is longer.
    2. **Baseline** — run backtest on `{primary_coin}/{primary_tf}` from `date_from` → `2026-05-31` with default params. Verifies the strategy is functional.
    3. **Register in settings.py NOW** with default params — do NOT defer. Set `"coins"` and `"timeframes"` from the card. Use the default risk block: `{"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10, "trading_fee": 0.0005, "maintenance_margin_rate": 0.005}`.
    4. **Finetune** — run Optuna optimization:
       ```bash
       python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id {id}
       ```
       This auto-updates settings.py params AND the strategy `__init__` defaults with the best-found values. Let it complete — it auto-scales trials (min 100).
    5. **Final backtest** — re-run with finetuned params on the same `{primary_coin}/{primary_tf}`. Use THESE metrics (not defaults) in the dev report.
    6. **Cross-asset checks** — run the same timeframe on the other coins listed in the card (e.g. if card says `coins: BTC, ETH, SOL` and primary tf is `15m`, run ETH/15m and SOL/15m). Do NOT use a different timeframe for cross-asset checks.
    7. **Dev report** — fill `references/dev_report_template.md` with finetuned metrics and save to `phase_6_agent_monitor/alpha_forge_v2/dev_report/{YYYYMMDD}_{strategy_id}_{strategy_name}_dev.md`.
    8. Update the Candidate Card in `factor_library/`: `status: IMPLEMENTED`.
- **On finetune failure** (crash, 0 trades after Optuna): keep default params, note the issue in the dev report, continue to WFO with defaults.
- **Note**: Even if the strategy is later REJECTED at WFO/PBO, settings.py retains the entry with best-found params. The crypto-strategy-tuner can rescan and attempt to salvage it later.
- **Mandatory Output**: `[5/8] DEV_REPORT: {coin}/{tf} {date_from}→2026-05-31 | Baseline → finetune → final backtest → cross-asset ({other coins}/{tf}) → dev report...`

## STAGE 6: WFO_EVO
- **Goal**: Stability check.
- **Instruction**: Check performance stability across 4 sliding windows. If unstable → mark as REJECTED.
- **Mandatory Output**: `[6/8] WFO_EVO: Running Walk-Forward Stability check (4-Window)...`

## STAGE 7: PBO_AUDIT
- **Goal**: Overfit check.
- **Instruction**: Run PBO check. If PBO > 0.40 → mark as REJECTED.
- **Mandatory Output**: `[7/8] PBO_AUDIT: Auditing Overfitting Probability (Threshold 0.40)...`

## ON_FAIL: AUTOPSY (Any Stage)
If a strategy crashes at **any stage** (TA_BAD_PARAM, import error, unfixable zero-trade smoke test, unresolvable AST error, WFO/PBO rejection):
1. Write an autopsy to `phase_6_agent_monitor/alpha_forge_v2/autopsy_report/{YYYYMMDD}_{strategy_id}_{strategy_name}_autopsy.md`.
   - Include: stage where failure occurred, exact error message, parameters at time of crash, root cause diagnosis.
2. Update the Candidate Card in `factor_library/`: `status: REJECTED`.
3. **KEEP the settings.py entry — do NOT remove it.** Use the best params found (Optuna best if finetune ran; defaults if it crashed before Stage 5). A rejected strategy must still be visible in the backtest tab so it can be manually inspected or salvaged later.
4. **Update scan_results.json** so the strategy appears in the dashboard:
   ```bash
   python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py
   python .gemini/skills/crypto-strategy-tuner/scripts/classify_strategies.py
   ```
5. Send a `FACTOR_FAILURE_REPORT` inbox message to `@crypto-strategy-tuner` so it can attempt to tune or re-grade it.
- **Mandatory Output**: `[!] AUTOPSY: Strategy REJECTED at Stage <N>. Retaining settings.py entry, updating scan_results.json, documenting failure...`

---

## STAGE 8: MANIFEST
- **Goal**: Final Validation & Notification.
- **Instruction**:
    1. **Registration guard** — run `python .gemini/skills/crypto-strategy-tuner/scripts/check_registration.py`. If it prints unregistered classes, add them to `settings.py` immediately (use `--fix` flag for auto-stub, then fill params).
    2. Confirm `settings.py` params reflect the Optuna best from Stage 5 finetune — do NOT overwrite with WFO window-specific params. WFO tests stability, it does not produce better params.
    3. **Update the backtest dashboard** — run scan + classify so the new strategy appears in the UI with its grade:
       ```bash
       python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py
       python .gemini/skills/crypto-strategy-tuner/scripts/classify_strategies.py
       ```
    4. Sync metrics to Obsidian card via `utility/sync_backtest_to_obsidian.py`.
    5. Update the Candidate Card in `factor_library/`: `status: VALIDATED`.
    6. Notify `@crypto-fullstack`.
- **Mandatory Output**: `[8/8] MANIFEST: Guard check → scan + classify → Obsidian sync → VALIDATED...`
