# Phase 7 — Pattern Discovery System Flow
> Last updated: 2026-06-16 (compound simulation, Overview tab, chain context bar, overlap fix, cache fix, invalid range bounds fix)
> Regime-aware parameter mining across 165 time windows → Wisdom Matrix

---

## OVERVIEW

Phase 7 answers a single question:
> *"Which parameter set works best for this strategy in this market regime and time horizon?"*

Instead of optimizing once over the full history, Phase 7 slices time into **165 overlapping windows** (MICRO / MESO / MACRO), runs Optuna on each slice, classifies the market regime for that slice, and stores everything in a **Wisdom Matrix CSV**. The result is a lookup table of regime-aware best params across all mined strategies.

---

## SYSTEM ARCHITECTURE

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         PHASE 7 — PATTERN DISCOVERY                       │
│                                                                           │
│  ┌─────────────────┐    ┌──────────────────────────────────────────────┐  │
│  │  Claude Agent   │    │              Dashboard (index.html)          │  │
│  │  /phase7-tuner  │    │                                              │  │
│  │                 │    │  Mining Control ─── START / STOP / PATCH /   │  │
│  │  ① probe 3 wins │    │                     🤖 TUNE RANGES           │  │
│  │  ② detect edges │    │  Monitor window ─── live stdout stream       │  │
│  │  ③ widen ranges │    │  Wisdom table   ─── 915 rows, click-to-sort  │  │
│  │  ④ mine / report│    │  Detail panel   ─── 5 tabs per row           │  │
│  └────────┬────────┘    │  Summary cards  ─── best per strategy        │  │
│           │             └─────────────────────┬────────────────────────┘  │
│           │                                   │                           │
│           └──────────────────┬────────────────┘                           │
│                              │  HTTP                                       │
│                              ▼                                             │
│                   ┌──────────────────────┐                                 │
│                   │   main_controller/   │  Flask API                     │
│                   │   main.py            │  POST /api/phase_7/            │
│                   │                      │    trigger_mining              │
│                   │                      │    stop_mining                 │
│                   │                      │    status                      │
│                   │                      │    patch_results               │
│                   │                      │    run_tuner                   │
│                   └──────────┬───────────┘                                 │
│                              │  subprocess                                 │
│                              ▼                                             │
│                   ┌──────────────────────┐                                 │
│                   │   phase_7/miner.py   │  Per-strategy orchestrator     │
│                   │                      │                                 │
│                   │  for each window:    │                                 │
│                   │    ① load_data()    │                                 │
│                   │    ② classify_regime│                                 │
│                   │    ③ optimize_window│                                 │
│                   │    ④ verify run     │                                 │
│                   │    ⑤ save JSON      │                                 │
│                   │  merge wisdom CSV   │                                 │
│                   └──────────┬───────────┘                                 │
│                              │                                             │
│          ┌───────────────────┼────────────────────┐                        │
│          ▼                   ▼                    ▼                        │
│  window_tuner.py    regime_classifier.py   raw_results/                   │
│  Optuna optimizer   Bull/Bear/Chop/Range   sid_10_1M_2024-01-01.json      │
│  DEFAULT_RANGES     from price + vol       (equity curve + trades)        │
│                                                                           │
│          └───────────────────┬────────────────────┘                        │
│                              ▼                                             │
│                   wisdom_matrix.csv   ← the output                        │
│                   (one row per window × strategy)                          │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## KEY FILES

| File | Role |
|---|---|
| `phase_7/dashboard/index.html` | Full UI — mining control, wisdom table, detail panel, charts |
| `phase_7/miner.py` | Orchestrates mining for one strategy across all 165 windows |
| `phase_7/scripts/window_generator.py` | Generates `generated_windows.json` (run once, or when date range changes) |
| `phase_7/scripts/window_tuner.py` | Optuna optimizer — `DEFAULT_RANGES`, `MIN_TRADES`, early stopping |
| `phase_7/scripts/regime_classifier.py` | Classifies each window as `BULL_TREND / BEAR_TREND / HIGH_VOL_CHOP / LOW_VOL_RANGE` |
| `phase_7/scripts/patch_metrics.py` | Recomputes fees/slippage/win-loss on existing raw JSONs (retroactive fix) |
| `phase_7/agents/tuner_agent.py` | Claude agent script — probes, detects boundary hits, widens ranges |
| `.claude/commands/logs/LTM.md` | Tuner agent long-term memory (patterns across sessions) |
| `.claude/commands/logs/session_memory.md` | Tuner agent session memory (last 10 session summaries) |
| `.claude/commands/logs/activity_log.md` | Tuner agent timestamped activity trail |
| `phase_7/data/generated_windows.json` | 165 window definitions with type, category, date range, trial count |
| `phase_7/data/wisdom_matrix.csv` | Output — one row per (strategy × window), loaded by dashboard |
| `phase_7/data/raw_results/sid_X_TYPE_DATE.json` | Full result per window — equity curve, trades, best params |
| `main_controller/main.py` | Flask routes for all Phase 7 API endpoints |
| `.claude/commands/phase7-tuner.md` | Claude slash command definition |
| `strategy_backtest/settings.py` | `STRATEGY_LIBRARY` — all 110+ strategy configs |

---

## THE 165 WINDOWS

Generated by `window_generator.py` from 2023-01-01 → end of last complete month.

| Category | Types | Step | Trials | Purpose |
|---|---|---|---|---|
| MICRO | 1M, 2M | 1 month | 15 | Short-term regime patterns, scalper behaviour |
| MESO | 3M, 4M, 6M | 1–2 months | 25 | Medium-term trends, swing trade patterns |
| MACRO | 1Y, 2Y, 3Y | 6–36 months | 40 | Structural regimes, long-hold strategies |

Windows overlap by design — a 3M window starting 2024-01 and another starting 2024-02 share most of their data. This reveals how stable the best params are across adjacent time periods.

---

## MINING FLOW (per strategy)

```
miner.py --strategy_id 10
      │
      ├─ Load generated_windows.json  (165 windows)
      │
      └─ for each window:
            │
            ├─ [SKIP] If cached result exists and --no_resume not set → use stored summary
            │
            ├─ load_data(coin, tf, start, end)
            │     └─ [SKIP] if bars < MIN_BARS for this window type
            │
            ├─ classify_regime(start, end)
            │     └─ returns: BULL_TREND / BEAR_TREND / HIGH_VOL_CHOP / LOW_VOL_RANGE + score
            │
            ├─ optimize_window(df, strat_cls, base_params, risk, n_trials)  ← window_tuner.py
            │     ├─ Merge DEFAULT_RANGES + strat_cls.OPTIMIZATION_RANGES
            │     ├─ Split params into tunable (have a range) and fixed (don't)
            │     ├─ Run Optuna TPE (multivariate, seed=42, n_startup=5)
            │     ├─ _EarlyStopping(patience=6) — stops if Sharpe flat for 6 trials
            │     └─ Returns: best_params, best_sharpe, best_trial_num, actual_trials_run
            │
            ├─ Verification run — BacktestEngine with best_params
            │     └─ Capture: equity curve, trades, fees, slippage, win/loss
            │
            ├─ Save raw JSON → phase_7/data/raw_results/sid_10_1M_2024-01-01.json
            │     Contains: all metrics + equity_curve[] + trades_detail[]
            │
            └─ Append CSV summary → wisdom_matrix.csv row

      └─ merge_wisdom_matrix() — replaces all rows for this strategy_id in the CSV
```

Progress lines printed to stdout:
```
TOTAL_WINDOWS:165
PROGRESS:1/165:0.6:MICRO:1M:2023-01-01
PROGRESS:2/165:1.2:MICRO:1M:2023-02-01
...
DONE:163:915
```

The dashboard parses these to drive the live monitor.

---

## WINDOW TUNER — PARAMETER RANGES

`window_tuner.py` defines which params are tunable and what bounds the optimizer explores.

### Priority order
```
strategy.OPTIMIZATION_RANGES   ← highest priority (strategy-specific, overrides defaults)
         +
DEFAULT_RANGES                 ← fallback for any param name not in OPTIMIZATION_RANGES
         =
effective_ranges               ← what the optimizer actually uses
```

Any param in `settings.py` `"params"` that is NOT in either dict is **fixed** at the `settings.py` value and never optimized.

### Detecting untunable params
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from phase_7.scripts.window_tuner import DEFAULT_RANGES
from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies as strat_reg

sid = '10'
cfg = STRATEGY_LIBRARY[sid]
cls = getattr(strat_reg, cfg['class'])
ranges = dict(DEFAULT_RANGES)
if hasattr(cls, 'OPTIMIZATION_RANGES'): ranges.update(cls.OPTIMIZATION_RANGES)
fixed = [k for k in cfg['params'] if k not in ranges]
print('Fixed (untunable):', fixed or 'none — all good!')
"
```

### Range type conventions

| Range type | Example | Optuna call |
|---|---|---|
| Integer tuple `(lo, hi)` | `'period': (5, 50)` | `suggest_int` |
| Float tuple `(lo, hi)` | `'sl_pct': (0.01, 0.20)` | `suggest_float` |
| List (categorical) | `'trend_filter': [True, False]` | `suggest_categorical` |

### Early stopping
```python
MIN_TRADES = 5      # trials with fewer round trips → score = -999
PATIENCE   = 6      # stop if best Sharpe doesn't improve for 6 consecutive trials
```

`converged = actual_trials_run < n_trials` — True only when early stopping fires.

### Valid lower bound rule

Any integer period param with lower bound 0 wastes trial budget — `rolling(window=0)` raises a ValueError (caught as -999), and `max_hold_bars=0` exits every trade immediately. Lower bounds must be ≥ 1 for periods and ≥ 2 for hold bars.

Fixed in DEFAULT_RANGES (2026-06-16):
- `max_hold_bars: (0, 48)` → `(2, 48)`
- `kdj_period: (0, 30)` → `(3, 30)`

---

## REGIME CLASSIFICATION

Every window gets one of four labels:

| Regime | Meaning | Visual colour |
|---|---|---|
| `BULL_TREND` | Upward trending price, moderate vol | Green |
| `BEAR_TREND` | Downward trending price | Red |
| `HIGH_VOL_CHOP` | High volatility, no clear trend | Yellow |
| `LOW_VOL_RANGE` | Low volatility, sideways/ranging | Grey |

The regime label is stored in both the raw JSON and the wisdom CSV, and drives all chart groupings in the dashboard.

---

## RAW RESULT JSON SCHEMA

`phase_7/data/raw_results/sid_{id}_{type}_{start}.json`

```json
{
  "strategy_id":       "10",
  "category":          "MICRO",
  "window_type":       "1M",
  "start_date":        "2024-01-01",
  "end_date":          "2024-01-31",
  "regime":            "BULL_TREND",
  "regime_score":      0.72,
  "market_features":   "{\"atr_pct\": 3.2, \"rsi_end\": 61.4, \"annual_vol\": 48.2}",
  "roi":               12.34,
  "sharpe":            1.82,
  "mdd":               8.7,
  "trades":            27,
  "profit_factor":     2.1,
  "params":            "{\"bb_period\": 34, \"bb_std\": 2.8, ...}",
  "trials_budget":     15,
  "best_trial_num":    9,
  "converged":         true,
  "initial_balance":   1000.0,
  "final_balance":     1123.4,
  "net_profit":        123.4,
  "gross_profit":      145.2,
  "gross_loss":        21.8,
  "total_fees":        12.3,
  "total_slippage":    2.14,
  "win_rate":          "62.50%",
  "winning_trades":    17,
  "losing_trades":     10,
  "avg_duration_days": "1.3",
  "equity_curve":      [1000.0, 1012.3, ...],
  "trades_detail":     [{"type": "BUY", "time": "...", ...}, ...]
}
```

---

## WISDOM MATRIX CSV SCHEMA

`phase_7/data/wisdom_matrix.csv` — one row per (strategy × window)

| Column | Type | Notes |
|---|---|---|
| `strategy_id` | str | Numeric string key from STRATEGY_LIBRARY |
| `category` | str | MICRO / MESO / MACRO |
| `window_type` | str | 1M / 2M / 3M / 4M / 6M / 1Y / 2Y / 3Y |
| `start_date` | str | YYYY-MM-DD |
| `end_date` | str | YYYY-MM-DD |
| `regime` | str | BULL_TREND etc. |
| `regime_score` | float | 0–1 confidence |
| `roi` | float | % return |
| `sharpe` | float | Sharpe ratio |
| `mdd` | float | Max drawdown % |
| `trades` | int | Completed round trips |
| `market_features` | JSON str | ATR%, RSI, vol%, etc. |
| `params` | JSON str | Best params found by Optuna |

---

## FLASK API ENDPOINTS

All routes are in `main_controller/main.py` under the `_p7` state block.

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/phase_7/trigger_mining` | Start miner for a strategy. Body: `{strategy_id, trials?, no_resume?}` |
| `GET` | `/api/phase_7/status` | Returns `{is_running, last_logs[], status.last_run}` |
| `POST` | `/api/phase_7/stop_mining` | Send SIGTERM to running miner/tuner process |
| `POST` | `/api/phase_7/patch_results` | Run `patch_metrics.py` to recompute metrics on old JSONs |
| `POST` | `/api/phase_7/run_tuner` | Start tuner agent for a strategy. Body: `{strategy_id, probe_trials?, max_iter?, run_miner?}` |
| `GET` | `/api/phase_7/compound/<strategy_id>` | Compound capital simulation. Query: `?capital=1000`. Returns chain per window type. |
| `GET` | `/api/phase_7/agent_log` | Returns `{content: LTM.md string, live_logs: [], is_running: bool}` |

The server holds a single `_p7` dict:
```python
_p7 = {
    'proc':       None,     # active Popen
    'logs':       [],       # rolling stdout (capped at 300 lines)
    'is_running': False,
    'last_run':   None,     # ISO timestamp of last completion
}
```

A background thread (`_p7_stdout_reader`) drains proc stdout into `_p7['logs']` and sets `is_running = False` when the process exits.

---

## DASHBOARD FEATURES

### Top-level tab navigation
Two main tabs: **📊 Overview** (default) and **🧠 Wisdom Matrix**.

---

### Overview Tab (`#overview-section`)

The Overview tab runs a **compound capital simulation** — it chains the best windows of each type sequentially and shows how capital would have grown.

**Controls:**
- Strategy selector (auto-populated from CSV)
- Starting capital input (default $1,000)
- **Load** button → fetches `/api/phase_7/compound/<sid>?capital=<N>`

**Stat cards (4):**
| Card | Content |
|---|---|
| Starting Capital | User-entered capital |
| Best Chain | Window type with highest total ROI + final capital |
| Worst Chain | Window type with lowest total ROI |
| Profitable Chains | Count of chains with total ROI > 0 |

**Compound growth chart** — Plotly multi-line, one line per window type, with a dotted breakeven reference line. Subtitle updates dynamically to show the selected capital amount.

**Chain breakdown table** — click a row to render a window-by-window bar chart on the right showing capital at each step (green = profitable window, red = loss).

---

### Tuner Agent Panel (`#agent-panel`)

Collapsible panel above the main tab nav. Shows:
- **Live Output** — real-time stdout stream from the tuner agent (same source as Monitor)
- **Change Log (LTM.md)** — all past tuner runs with timestamps, strategy IDs, and ranges widened. Fetched from `/api/phase_7/agent_log`.
- **🔄 refresh** button on LTM panel

---

### Mining Control Center
- **Strategy dropdown** — all 110+ strategies from `/api/strategy_list`
- **Trials override** — per-window trial count override (default: auto from window spec)
- **Force re-mine toggle** — ignores cached results, re-optimises all windows
- **START MINING** — triggers `/api/phase_7/trigger_mining`
- **STOP** (red) — appears while any Phase 7 process is running, triggers `/api/phase_7/stop_mining`
- **PATCH RESULTS** — triggers `/api/phase_7/patch_results` (fixes old JSONs)
- **TUNE RANGES** (🤖, teal) — triggers `/api/phase_7/run_tuner`; probes 3 representative windows and auto-widens any params hitting range boundaries; output streams to the Monitor window
- **Monitor** — floating draggable window with progress bar, per-window status, live log; badge shows `TUNER` (teal) or `MINER` (blue) depending on active process

---

### Wisdom Matrix Tab (`#wisdom-section`)

#### Wisdom Table
- **Click-to-sort** on Strategy, Type, Start Date, ROI, Sharpe, MDD, Trades columns
- **Tab filter** — ALL / MICRO / MESO / MACRO with sub-type pills
- **Strategy + Regime filters** in filter bar
- **Row click** — opens detail panel below table for that window

#### Detail Panel (5 tabs)
| Tab | Content |
|---|---|
| Metrics | Market features strip · Optimized params grid · Account / Edge / Trade stats cards |
| Equity Curve | Plotly line chart with initial balance reference line |
| Entry & Exit | Scatter plot — entry/exit price points with win/loss connector lines |
| Periodic Returns | Monthly + yearly net P&L bar charts |
| Trade Log | Full round-trip table — Entry/Exit time, Side, Prices, Fees, Slippage, Net P&L, Duration, Reason |

**Chain Context Bar** (`#dp-chain-bar`) — shown above the tab bar in the detail panel. Displays the selected window's position within the compound chain for its window type:
```
🔗 1M Chain   Window 12/41   Capital in: $1,123.45  →  $1,089.22  (-$34.23, -3.05%)
```
- Capital values reflect the user's selected starting capital from the Overview input
- Shows `🟢 Chain start` or `🏁 Chain end` badges for first/last windows

#### Summary Cards
- One card per mined strategy, sorted numerically by strategy ID
- Best Sharpe per category (MICRO / MESO / MACRO) with clickable rows to filter table

---

## COMPOUND CAPITAL SIMULATION

### Endpoint: `GET /api/phase_7/compound/<strategy_id>?capital=1000`

Reads `wisdom_matrix.csv`, groups rows by `window_type`, then for each type builds a **non-overlapping sequential chain** and compounds capital through it.

### Non-overlapping filter (critical)

Windows in Phase 7 are generated with overlapping step sizes (e.g. 3M windows step 1 month → consecutive windows share 2 months of data). Compounding overlapping windows double-counts time periods. The endpoint filters each chain to non-overlapping windows only:

```python
non_overlapping = []
last_end = None
for r in sorted_rows:                          # sorted by start_date
    if last_end is None or r['start_date'] >= last_end:
        non_overlapping.append(r)
        last_end = r.get('end_date', '')
```

Effect on window count per chain:

| Type | Duration | Step | Overlap | Windows kept |
|------|----------|------|---------|--------------|
| 1M   | 1M       | 1M   | none    | all (~41)    |
| 2M   | 2M       | 1M   | 1M      | ~20          |
| 3M   | 3M       | 1M   | 2M      | ~13          |
| 4M   | 4M       | 2M   | 2M      | ~10          |
| 6M   | 6M       | 2M   | 4M      | ~6           |
| 1Y   | 12M      | 6M   | 6M      | ~3           |
| 2Y   | 24M      | 12M  | 12M     | ~1-2         |
| 3Y   | 36M      | 36M  | none    | 1            |

### Compound formula

```python
end_capital = capital * (1 + roi / 100)   # roi is net % (after fees/slippage)
peak        = max(peak, end_capital)
dd          = (peak - end_capital) / peak * 100
max_dd      = max(max_dd, dd)
capital     = end_capital                  # full precision, not rounded mid-loop
```

The `start_capital` and `end_capital` stored in each chain entry are rounded to 2 decimal places for display only. The running `capital` variable preserves full float precision.

### Response schema

```json
{
  "strategy_id": "36",
  "start_capital": 1000.0,
  "chains": {
    "1M": {
      "chain": [
        {
          "start_date": "2023-01-01",
          "end_date":   "2023-01-31",
          "regime":     "BULL_TREND",
          "window_roi": 12.34,
          "sharpe":     1.820,
          "start_capital": 1000.00,
          "end_capital":   1123.40
        }, ...
      ],
      "final_capital": 8682.25,
      "total_roi":     768.23,
      "max_drawdown":  14.2,
      "windows":       41
    },
    "2M": { ... },
    ...
  }
}
```

### Client-side caching

`_compoundCache` in the dashboard caches compound data keyed by `{strategy_id}_{capital}`. Cache is cleared in `reloadData()` after mining completes so chain data reflects newly mined windows.

---

## CLAUDE AGENT — /phase7-tuner

The Phase 7 Tuner Agent wraps the manual range-checking process into an automated loop.

### Invocation

**From Claude (slash command):**
```
/phase7-tuner <strategy_id> [--probe_trials N] [--max_iter N] [--run_miner]
```

**From the Dashboard:**
Select a strategy in the Mining Control Center → click **🤖 Tune Ranges** → output streams to the Monitor window (phase badge shows `TUNER` in teal).

**From terminal:**
```bash
# Just check and adjust ranges:
venv/bin/python phase_7/agents/tuner_agent.py --strategy_id 10

# Check ranges then immediately run full miner:
venv/bin/python phase_7/agents/tuner_agent.py --strategy_id 10 --run_miner

# More probe trials, fewer iterations:
venv/bin/python phase_7/agents/tuner_agent.py --strategy_id 10 --probe_trials 50 --max_iter 3
```

### What it does
```
① Read .claude/commands/logs/session_memory.md + LTM.md  (historical context)
② Validate strategy exists in settings.py
③ Run tuner_agent.py:
      ↓ probe 3 representative windows — one per category at index len//3
            MICRO → 1M window  (stable mid-range, not the latest window)
            MESO  → 3M window
            MACRO → 1Y window
      ↓ run probe_trials Optuna trials per window
      ↓ check each best param: within BOUNDARY_TOLERANCE (5%) of range edge?
      ↓ if yes → record direction (lo/hi hit) + source (DEFAULT_RANGES or OPTIMIZATION_RANGES)
      ↓ route edits based on source:
            source = DEFAULT_RANGES     → widen in phase_7/scripts/window_tuner.py
            source = OPTIMIZATION_RANGES → widen in the strategy class .py file
      ↓ widen by WIDEN_FACTOR (60% of current span) in the correct direction
      ↓ reload ranges → repeat until stable (max_iter iterations, default 5)
④ Report: which ranges were widened, source file, which params are still untunable
⑤ Ask: "Run full Phase 7 miner now?"
⑥ Append insight to .claude/commands/logs/LTM.md + session_memory.md + activity_log.md
```

### Probe window selection (fixed)

```python
PROBE_TYPES = {'MICRO': '1M', 'MESO': '3M', 'MACRO': '1Y'}

def get_probe_windows():
    for cat, preferred_type in PROBE_TYPES.items():
        typed = [w for w in windows if w['category'] == cat and w['type'] == preferred_type]
        if typed:
            idx = max(0, len(typed) // 3)   # stable mid-list, not latest
            result.append(typed[idx])
```

This picks one stable, non-bleeding-edge window per category. Typical selection:
- `1M 2024-02` (MICRO)
- `3M 2024-02` (MESO)
- `1Y 2023-07` (MACRO)

### Boundary hit detection

```python
BOUNDARY_TOLERANCE = 0.05   # within 5% of edge → hit
WIDEN_FACTOR       = 0.60   # widen by 60% of current span

hits[param] = {
    'direction': 'lo' | 'hi',
    'range':     (lo, hi),     # original types preserved (int stays int, float stays float)
    'best':      best_value,
    'source':    'DEFAULT_RANGES' | 'OPTIMIZATION_RANGES',
}
```

### Range edit routing

```python
if info['source'] == 'OPTIMIZATION_RANGES':
    widen_range_in_strategy_file(cls_name, param, direction, old_lo, old_hi)
    # → edits strat_cls.OPTIMIZATION_RANGES in the strategy .py class file
else:
    widen_range_in_tuner(param, direction, old_lo, old_hi)
    # → edits DEFAULT_RANGES in phase_7/scripts/window_tuner.py
```

### Type-aware regex (fixed)

Before the fix, `5` (int) would be formatted as `"5.0"` (float string), causing the primary regex to silently fail and fall through to an untargeted fallback.

```python
def _fmt_range_val(v):
    """5.0 → '5'  |  1.5 → '1.5'  |  30 → '30'"""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)

def _apply_range_edit(content, param, old_lo, old_hi, new_lo, new_hi):
    lo_str = _fmt_range_val(old_lo)
    hi_str = _fmt_range_val(old_hi)
    # primary: exact match using formatted values
    pattern = r"('" + re.escape(param) + r"'\s*:\s*)\(\s*" \
              + re.escape(lo_str) + r"\s*,\s*" + re.escape(hi_str) + r"\s*\)"
    new_content, n = re.subn(pattern, r'\g<1>' + new_range, content)
    if n > 0: return new_content, True
    # fallback: numeric-only match for any float/int values
    pattern2 = r"('" + re.escape(param) + r"'\s*:\s*)\(\s*[\d.eE+-]+\s*,\s*[\d.eE+-]+\s*\)"
    ...
```

### Tuner agent files

```
phase_7/agents/
  tuner_agent.py              ← probe + boundary detection + range edit loop
.claude/commands/
  phase7-tuner.md             ← slash command definition (equivalent to Gemini SKILL.md)
  logs/
    LTM.md                    ← long-term memory (patterns across sessions)
    session_memory.md         ← last 10 session summaries
    activity_log.md           ← timestamped activity trail
```

### Key functions in tuner_agent.py

| Function | Purpose |
|---|---|
| `get_probe_windows()` | Pick 3 stable representative windows (1/3 position per category) |
| `find_boundary_hits(probe_results, ranges, strat_cls)` | Returns dict of params hitting range edges, with `source` routing field |
| `_fmt_range_val(v)` | Format range value as it appears in source file (5.0 → `"5"`) |
| `_apply_range_edit(content, param, old_lo, old_hi, new_lo, new_hi)` | Type-aware primary regex + numeric fallback |
| `widen_range_in_tuner(param, direction, old_lo, old_hi)` | Edit `DEFAULT_RANGES` in `window_tuner.py` |
| `find_strategy_file(cls_name)` | Locate the `.py` file containing `class {cls_name}` in `strategies/` |
| `widen_range_in_strategy_file(cls_name, param, direction, old_lo, old_hi)` | Edit `OPTIMIZATION_RANGES` in the strategy class file |

---

## ADDING A NEW STRATEGY TO PHASE 7

1. **Create the strategy class** in `strategy_backtest/strategies/my_strategy.py`
   - Inherit from `BaseStrategy`
   - `__init__(self, df, param_a, param_b, **kwargs)` + call `super().__init__(..., **kwargs)`
   - Implement `generate_signals(self) -> pd.DataFrame` with a `signal` column (-1 / 0 / 1)
   - Optional: `OPTIMIZATION_RANGES = {'param_a': (1, 50), ...}` for params not in DEFAULT_RANGES
   - Optional: `@classmethod validate_params(cls, params) -> bool` to reject degenerate combos

2. **Register in `settings.py`**
   ```python
   "111": {
       "id": "MY_STRATEGY_BTC_1H",
       "class": "MyStrategy",
       "data":  {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
       "risk":  {"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
       "params": {"param_a": 14, "param_b": 0.03},
   }
   ```
   *(The `strategies/__init__.py` auto-imports all .py files — no manual import needed)*

3. **Check all params are tunable**
   ```bash
   /phase7-tuner 111
   ```
   The agent will detect any untunable params and widen ranges where needed.

4. **Run full Phase 7 mining**
   Dashboard → select strategy → START MINING, or:
   ```bash
   venv/bin/python phase_7/miner.py --strategy_id 111
   ```

---

## KNOWN BEHAVIOURS

- **Strategies 1 and 5** — only 45 windows each (types: 4M, 6M, 1Y, 2Y, 3Y). These strategies use daily timeframe, so 1M/2M/3M windows have too few bars (< MIN_BARS) and are skipped. This is correct behaviour, not a bug.
- **SOL taker column** — SOL's parquet has string values in the taker buy volume column. `regime_classifier.py` wraps the ratio calculation in `pd.to_numeric(errors='coerce')` + try/except to handle this gracefully.

---

## CURRENT MINING STATUS (as of 2026-06-16)

| Metric | Value |
|---|---|
| Total strategies in library | 110+ |
| Strategies mined | 9 (IDs: 1, 2, 5, 8, 10, 36, 75, 86, 92) |
| Total wisdom matrix rows | 1,245 |
| Windows per strategy | 165 (45 for daily-TF strategies) |
| Date coverage | 2023-01-01 → 2026-05-31 |
| Params fixed (invalid bounds) | `max_hold_bars`, `kdj_period` lower bound corrected 2026-06-16 |
| Strategy 36 OPTIMIZATION_RANGES | Updated 2026-06-16 — added `ema_slope_thresh`, `use_pattern_filter`, `use_vol_filter` |
