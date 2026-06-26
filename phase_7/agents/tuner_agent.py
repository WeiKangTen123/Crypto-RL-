"""
Phase 7 Tuner Agent — autonomous parameter range checker and optimizer.

Workflow:
  1. Read strategy config from settings.py
  2. Run a quick probe (one stable window per category: MICRO / MESO / MACRO)
  3. Check if any best param is within BOUNDARY_TOLERANCE of its range limit
  4. Widen that range in window_tuner.py DEFAULT_RANGES OR strategy OPTIMIZATION_RANGES
  5. Repeat until no boundary hits OR max_iter reached
  6. Optionally launch the full Phase 7 miner afterwards

Usage:
  python phase_7/agents/tuner_agent.py --strategy_id 10
  python phase_7/agents/tuner_agent.py --strategy_id 10 --probe_trials 40 --max_iter 4
  python phase_7/agents/tuner_agent.py --strategy_id 10 --run_miner
"""

import os
import sys
import json
import re
import argparse
import importlib
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

_script_dir = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(os.path.dirname(_script_dir))   # .../Crypto-RL
sys.path.insert(0, ROOT_DIR)

TUNER_FILE      = os.path.join(ROOT_DIR, 'phase_7', 'scripts', 'window_tuner.py')
STRATEGIES_DIR  = os.path.join(ROOT_DIR, 'strategy_backtest', 'strategies')
WINDOWS_FILE    = os.path.join(ROOT_DIR, 'phase_7', 'data', 'generated_windows.json')
LTM_FILE        = os.path.join(_script_dir, 'LTM.md')
VENV_PYTHON     = os.path.join(ROOT_DIR, 'venv', 'bin', 'python')

BOUNDARY_TOLERANCE = 0.05   # flag param if within 5% of range edge
WIDEN_FACTOR       = 0.60   # extend boundary by 60% of current span

# Preferred window type per category for probing — stable, enough bars, not bleeding-edge
PROBE_TYPES = {'MICRO': '1M', 'MESO': '3M', 'MACRO': '1Y'}


# ── Helpers ────────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _reload_tuner():
    """Re-import window_tuner so file edits are picked up each iteration."""
    import phase_7.scripts.window_tuner as wt
    importlib.reload(wt)
    return wt


def get_effective_ranges(strat_cls):
    """Merge DEFAULT_RANGES + strategy OPTIMIZATION_RANGES (same logic as window_tuner)."""
    wt = _reload_tuner()
    ranges = dict(wt.DEFAULT_RANGES)
    if hasattr(strat_cls, 'OPTIMIZATION_RANGES'):
        ranges.update(strat_cls.OPTIMIZATION_RANGES)
    return ranges


def get_probe_windows():
    """
    Pick one stable window per category using the preferred type (1M / 3M / 1Y).
    Selects from the first third of the list — not bleeding-edge recent,
    not too old, reproducible across runs.
    """
    if not os.path.exists(WINDOWS_FILE):
        return []
    with open(WINDOWS_FILE) as f:
        windows = json.load(f)

    result = []
    for cat, preferred_type in PROBE_TYPES.items():
        # Prefer the defined type; fall back to any window in this category
        typed = [w for w in windows if w['category'] == cat and w['type'] == preferred_type]
        if not typed:
            typed = [w for w in windows if w['category'] == cat]
        if typed:
            # Pick from the first third — stable period with reliable data
            idx = max(0, len(typed) // 3)
            result.append(typed[idx])

    return result


# ── Probe ──────────────────────────────────────────────────────────────────────

def probe_strategy(sid, strat_cls, cfg, n_trials):
    """
    Run optimize_window on one MICRO / MESO / MACRO window each.
    Returns list of {window, best_params, best_sharpe}.
    """
    from strategy_backtest.run_backtest import load_data

    # Re-import optimize_window each call so reloaded DEFAULT_RANGES take effect
    wt = _reload_tuner()

    coin = cfg['data']['coins']
    tf   = cfg['data']['timeframes']

    MIN_BARS = {'1M': 30, '2M': 50, '3M': 80, '6M': 120, '1Y': 200, '2Y': 300, '3Y': 400}

    results = []
    for w in get_probe_windows():
        log(f"  Probing {w['category']:5s}  {w['type']}  {w['start']} → {w['end']}  [{n_trials} trials]")
        df = load_data(coin, tf, w['start'], w['end'])
        min_bars = MIN_BARS.get(w['type'], 30)
        if df is None or df.empty or len(df) < min_bars:
            log(f"  [SKIP] Only {len(df) if df is not None else 0} bars — need {min_bars}")
            continue
        try:
            best_params, best_sharpe, best_trial_num, actual_trials = wt.optimize_window(
                df, strat_cls, cfg['params'], cfg['risk'], n_trials=n_trials
            )
            log(f"  → Sharpe {best_sharpe:.3f}  best_trial={best_trial_num}/{actual_trials}")
            results.append({'window': w, 'best_params': best_params, 'best_sharpe': best_sharpe})
        except Exception as e:
            log(f"  [ERROR] {e}")
    return results


# ── Boundary detection ─────────────────────────────────────────────────────────

def find_boundary_hits(probe_results, ranges, strat_cls, tol=BOUNDARY_TOLERANCE):
    """
    For each numeric param across all probe results, check if best value is
    within `tol` fraction of the range boundary.
    Returns dict: {param: {direction, range, best, window_type, source}}
    source = 'OPTIMIZATION_RANGES' | 'DEFAULT_RANGES'
    """
    wt = _reload_tuner()
    opt_ranges = getattr(strat_cls, 'OPTIMIZATION_RANGES', {})

    hits = {}
    for result in probe_results:
        for k, v in result['best_params'].items():
            if k not in ranges:
                continue
            r = ranges[k]
            if isinstance(r, list):
                continue   # categorical — no boundary
            if isinstance(v, bool):
                continue
            lo, hi = r[0], r[1]   # preserve original types from the dict
            span = float(hi) - float(lo)
            if span <= 0:
                continue
            fv = float(v)
            up_gap   = (float(hi) - fv) / span
            down_gap = (fv - float(lo)) / span
            direction = None
            if up_gap < tol:
                direction = 'upper'
            elif down_gap < tol:
                direction = 'lower'
            if direction and k not in hits:
                source = 'OPTIMIZATION_RANGES' if k in opt_ranges else 'DEFAULT_RANGES'
                hits[k] = {
                    'direction':   direction,
                    'range':       (lo, hi),     # original types preserved
                    'best':        fv,
                    'window_type': result['window']['type'],
                    'source':      source,
                }
    return hits


# ── Range editing ──────────────────────────────────────────────────────────────

def _fmt_range_val(v):
    """Format a range value the way it appears in Python source (int vs float)."""
    if isinstance(v, float) and v == int(v):
        return str(int(v))   # 5.0 → "5"
    return str(v)


def _compute_new_bounds(old_lo, old_hi, direction):
    """Return (new_lo, new_hi) widened by WIDEN_FACTOR in the given direction."""
    span = float(old_hi) - float(old_lo)
    ext  = span * WIDEN_FACTOR
    if direction == 'upper':
        new_lo, new_hi = float(old_lo), float(old_hi) + ext
    else:
        new_lo = float(old_lo) - ext
        if float(old_lo) >= 0:
            new_lo = max(0.0, new_lo)
        new_hi = float(old_hi)
    # Preserve int vs float
    if isinstance(old_lo, int) or (isinstance(old_lo, float) and old_lo == int(old_lo)):
        return int(round(new_lo)), int(round(new_hi))
    return round(new_lo, 4), round(new_hi, 4)


def _apply_range_edit(content, param, old_lo, old_hi, new_lo, new_hi):
    """
    Replace the range for `param` in `content`.
    Uses type-aware primary pattern then falls back to looser match.
    Returns (new_content, success_bool).
    """
    new_range = f'({new_lo}, {new_hi})'
    lo_str    = _fmt_range_val(old_lo)
    hi_str    = _fmt_range_val(old_hi)

    # Primary — type-aware: matches "(5,   30)" correctly
    pattern = (
        r"('" + re.escape(param) + r"'\s*:\s*)"
        r"\(\s*" + re.escape(lo_str) + r"\s*,\s*" + re.escape(hi_str) + r"\s*\)"
    )
    new_content, n = re.subn(pattern, r'\g<1>' + new_range, content)
    if n > 0:
        return new_content, True

    # Fallback — matches any numeric tuple for this param name
    pattern2 = r"('" + re.escape(param) + r"'\s*:\s*)\(\s*[\d.eE+-]+\s*,\s*[\d.eE+-]+\s*\)"
    match = re.search(pattern2, content)
    if match:
        new_content = content[:match.start()] + match.group(1) + new_range + content[match.end():]
        return new_content, True

    return content, False


def _backup_file(fpath):
    """Write a timestamped .bak copy before any agent edit."""
    import shutil
    bak = fpath + '.bak'
    shutil.copy2(fpath, bak)


def widen_range_in_tuner(param, direction, old_lo, old_hi):
    """Edit DEFAULT_RANGES in window_tuner.py. Returns (new_lo, new_hi) or None."""
    with open(TUNER_FILE) as f:
        content = f.read()
    new_lo, new_hi = _compute_new_bounds(old_lo, old_hi, direction)
    new_content, ok = _apply_range_edit(content, param, old_lo, old_hi, new_lo, new_hi)
    if not ok:
        log(f"  [WARN] '{param}' not found in window_tuner.py DEFAULT_RANGES — cannot auto-edit")
        return None
    _backup_file(TUNER_FILE)
    with open(TUNER_FILE, 'w') as f:
        f.write(new_content)
    log(f"  ✓ [{param}]  ({old_lo}, {old_hi}) → ({new_lo}, {new_hi})  ({direction} bound widened in window_tuner.py)")
    return new_lo, new_hi


def find_strategy_file(cls_name):
    """Find the .py file in strategies/ that defines cls_name."""
    for fname in os.listdir(STRATEGIES_DIR):
        if not fname.endswith('.py') or fname.startswith('_'):
            continue
        fpath = os.path.join(STRATEGIES_DIR, fname)
        with open(fpath, encoding='utf-8', errors='replace') as f:
            if f'class {cls_name}' in f.read():
                return fpath
    return None


def widen_range_in_strategy_file(cls_name, param, direction, old_lo, old_hi):
    """Edit OPTIMIZATION_RANGES in the strategy class file. Returns (new_lo, new_hi) or None."""
    fpath = find_strategy_file(cls_name)
    if not fpath:
        log(f"  [WARN] Cannot find strategy file for class '{cls_name}'")
        return None
    with open(fpath, encoding='utf-8') as f:
        content = f.read()
    new_lo, new_hi = _compute_new_bounds(old_lo, old_hi, direction)
    new_content, ok = _apply_range_edit(content, param, old_lo, old_hi, new_lo, new_hi)
    if not ok:
        log(f"  [WARN] '{param}' not found in OPTIMIZATION_RANGES of {os.path.basename(fpath)}")
        return None
    _backup_file(fpath)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    log(f"  ✓ [{param}]  ({old_lo}, {old_hi}) → ({new_lo}, {new_hi})  ({direction} bound widened in {os.path.basename(fpath)})")
    return new_lo, new_hi


# ── LTM ───────────────────────────────────────────────────────────────────────

def append_ltm(entry):
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    line  = f"\n- **{today}**: {entry}"
    os.makedirs(os.path.dirname(LTM_FILE), exist_ok=True)
    with open(LTM_FILE, 'a') as f:
        f.write(line)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Phase 7 Tuner Agent')
    parser.add_argument('--strategy_id',  required=True, help='Strategy ID from STRATEGY_LIBRARY')
    parser.add_argument('--probe_trials', type=int, default=30,
                        help='Optuna trials per probe window (default 30 — fast)')
    parser.add_argument('--max_iter',     type=int, default=5,
                        help='Max adjustment iterations (default 5)')
    parser.add_argument('--run_miner',    action='store_true',
                        help='After range stabilisation, launch full Phase 7 miner')
    args = parser.parse_args()

    from strategy_backtest.settings import STRATEGY_LIBRARY
    import strategy_backtest.strategies as strat_reg

    sid = str(args.strategy_id)
    if sid not in STRATEGY_LIBRARY:
        print(f"ERROR: Strategy ID '{sid}' not found in STRATEGY_LIBRARY.")
        sys.exit(1)

    cfg       = STRATEGY_LIBRARY[sid]
    cls_name  = cfg['class']
    if not hasattr(strat_reg, cls_name):
        print(f"ERROR: Class '{cls_name}' not found in strategies module.")
        sys.exit(1)
    strat_cls = getattr(strat_reg, cls_name)

    log(f"═══ Phase 7 Tuner Agent ═══")
    log(f"Strategy  : {sid} — {cfg.get('id', cls_name)}")
    log(f"Class     : {cls_name}")
    log(f"Probe     : {args.probe_trials} trials × 3 windows ({', '.join(PROBE_TYPES.values())})")
    log(f"Max iter  : {args.max_iter}")
    if hasattr(strat_cls, 'OPTIMIZATION_RANGES'):
        log(f"Strat-level OPTIMIZATION_RANGES: {list(strat_cls.OPTIMIZATION_RANGES.keys())}")

    adjusted = {}   # {param: {'old', 'new', 'direction', 'source'}}
    iteration = 0

    while iteration < args.max_iter:
        iteration += 1
        log(f"\n── Iteration {iteration}/{args.max_iter} ──────────────────────")

        ranges  = get_effective_ranges(strat_cls)
        tunable = [k for k in cfg['params'] if k in ranges]
        fixed   = [k for k in cfg['params'] if k not in ranges]

        log(f"Tunable ({len(tunable)}): {tunable}")
        if fixed:
            log(f"Fixed (no range): {fixed}")

        probe_results = probe_strategy(sid, strat_cls, cfg, n_trials=args.probe_trials)
        if not probe_results:
            log("No probe data — check data availability. Aborting.")
            break

        hits = find_boundary_hits(probe_results, ranges, strat_cls)

        if not hits:
            log(f"\n✓ Stable — no boundary hits after {iteration} iteration(s).")
            break

        log(f"\n⚠ Boundary hits: {list(hits.keys())}")
        any_edit = False
        for param, info in hits.items():
            lo, hi = info['range']
            log(f"  {param}: best={info['best']:.4g}  range=({lo}, {hi})  "
                f"hit={info['direction']} bound  [{info['window_type']}]  source={info['source']}")

            # Route edit to the correct file
            if info['source'] == 'OPTIMIZATION_RANGES':
                result = widen_range_in_strategy_file(cls_name, param, info['direction'], lo, hi)
            else:
                result = widen_range_in_tuner(param, info['direction'], lo, hi)

            if result:
                adjusted[param] = {
                    'old': (lo, hi), 'new': result,
                    'direction': info['direction'], 'source': info['source']
                }
                any_edit = True

        if not any_edit:
            log("Could not auto-edit any ranges. Manual review needed.")
            break

    else:
        log(f"\n⚠ Max iterations ({args.max_iter}) reached — some params may still be at boundaries.")

    # ── Final report ──────────────────────────────────────────────────────────
    log("\n══════════════════════ REPORT ══════════════════════════")
    log(f"Strategy {sid} ({cls_name})")

    if adjusted:
        log(f"Ranges widened ({len(adjusted)} params):")
        for p, info in adjusted.items():
            log(f"  {p:<30s}  {str(info['old']):<20s} → {info['new']}  ({info['direction']}, in {info['source']})")
        entry = (
            f"Strategy {sid} ({cls_name}): widened {len(adjusted)} range(s) — "
            + "; ".join(f"{p}: {i['old']}→{i['new']} [{i['source']}]" for p, i in adjusted.items())
        )
        append_ltm(entry)
        log("\nwindow_tuner.py / strategy file updated. Re-run Phase 7 mining to use new ranges.")
    else:
        log("No range adjustments needed — all params within bounds.")
        append_ltm(f"Strategy {sid} ({cls_name}): probe completed — all ranges adequate.")

    # Report untunable params
    final_ranges = get_effective_ranges(strat_cls)
    still_fixed  = [k for k in cfg['params'] if k not in final_ranges]
    if still_fixed:
        log(f"\n⚠ UNTUNABLE PARAMS (no range defined anywhere): {still_fixed}")
        log("  → Add to DEFAULT_RANGES in window_tuner.py OR to the strategy's OPTIMIZATION_RANGES")

    # ── Optionally launch full miner ──────────────────────────────────────────
    if args.run_miner:
        import subprocess
        log(f"\n▶ Launching full Phase 7 miner for strategy {sid}...")
        miner_script = os.path.join(ROOT_DIR, 'phase_7', 'miner.py')
        subprocess.run([VENV_PYTHON, miner_script, '--strategy_id', sid], cwd=ROOT_DIR)

    log("\n═══ Phase 7 Tuner Agent done ═══")


if __name__ == '__main__':
    main()
