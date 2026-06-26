"""
finetune.py — runs Optuna parameter optimisation on a specific strategy.

Usage:
    python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id 9
    python .gemini/skills/crypto-strategy-tuner/scripts/finetune.py --strategy_id 9 --trials 50 --date_from 2023-01-01 --date_to 2024-01-01
"""

import os
import sys
import json
import re
import argparse
import shutil
import math
import pandas as pd
from datetime import datetime
from filelock import FileLock

_script_dir   = os.path.dirname(os.path.abspath(__file__))
_agent_skill_dir = os.path.dirname(_script_dir) # .gemini/skills/crypto-strategy-tuner
_skills_dir      = os.path.dirname(_agent_skill_dir) # .gemini/skills
_gemini_dir      = os.path.dirname(_skills_dir) # .gemini
ROOT_DIR         = os.path.dirname(_gemini_dir) # Crypto-RL
AGENT_DIR        = _agent_skill_dir
SCAN_FILE        = os.path.join(AGENT_DIR, 'data', 'scan_results.json')
RESULT_FILE      = os.path.join(AGENT_DIR, 'data', 'finetune_results.json')
SETTINGS_LOCK    = os.path.join(AGENT_DIR, 'data', '.settings.lock')
SCAN_LOCK        = os.path.join(AGENT_DIR, 'data', '.scan.lock')

# Import shared logger
sys.path.insert(0, os.path.join(ROOT_DIR, '.gemini', 'shared'))
from logger import log_to_agent

sys.path.insert(0, ROOT_DIR)

# Default parameter search ranges (int → suggest_int, float → suggest_float)
DEFAULT_RANGES = {
    # ── Generic ──────────────────────────────────────────────────────────────
    'period':               (5,    50),
    'length':               (5,    50),
    'lookback':             (5,    50),
    'smoothing':            (2,    20),
    # ── MACD ─────────────────────────────────────────────────────────────────
    'fast':                 (3,    30),
    'slow':                 (15,  100),
    'signal':               (3,    20),
    'macd_fast':            (3,    30),
    'macd_slow':            (15,  100),
    'macd_signal':          (3,    20),
    'fast_period':          (3,    30),
    'slow_period':          (15,  100),
    # ── KDJ ──────────────────────────────────────────────────────────────────
    'kdj_period':           (5,    30),
    'kdj_oversold':         (10,   40),
    'kdj_overbought':       (60,   90),
    # ── RSI ──────────────────────────────────────────────────────────────────
    'rsi_period':           (5,    30),
    'rsi_window':           (5,    30),
    'rsi_oversold':         (20,   40),
    'rsi_overbought':       (60,   80),
    'rsi_low':              (20,   40),
    'rsi_high':             (60,   80),
    'rsi_lower':            (20,   40),
    'rsi_upper':            (60,   80),
    'rsi_threshold':        (30,   70),
    'vrsi_period':          (5,    30),
    'vrsi_oversold':        (15,   35),
    'vrsi_overbought':      (65,   85),
    # ── EMA / SMA ────────────────────────────────────────────────────────────
    'ema_fast':             (5,    30),
    'ema_slow':             (20,  200),
    'ema_med':              (10,   60),
    'ema_period':           (10,  200),
    'ema_trend':            (50,  300),
    'ema_trend_4h':         (50,  300),
    'ema_window':           (5,    50),
    'ema_speed_period':     (3,    20),
    'trend_ema_period':     (50,  300),
    'sma_period':           (5,    50),
    'sma_macro':            (50,  300),
    'sma_macro_period':     (50,  300),
    'major_period':         (10,   50),
    'minor_period':         (5,    30),
    # ── ADX ──────────────────────────────────────────────────────────────────
    'adx_period':           (7,    30),
    'adx_threshold':        (15,   40),
    'adx_threshold_1h':     (15,   40),
    'adx_threshold_4h':     (15,   40),
    # ── ATR / Multipliers ────────────────────────────────────────────────────
    'atr_period':           (5,    30),
    'atr_multiplier':       (1.0,  6.0),
    'atr_multiplier_sl':    (0.5,  3.0),
    'atr_multiplier_tp':    (1.0,  8.0),
    'multiplier':           (1.0,  6.0),
    'multiplier_l1':        (1.0, 10.0),   # layered entry — needs range up to 4×+ ATR
    'multiplier_l2':        (1.0, 15.0),   # add-layer 2 — needs range up to 9×+ ATR
    'multiplier_l3':        (1.0, 15.0),   # add-layer 3 — needs range up to 5×+ ATR
    'tp_atr_mult':          (1.0,  8.0),
    'sl_atr_mult':          (0.5,  3.0),
    'sl_atr_multiplier':    (0.5,  3.0),
    'sl_multiplier':        (0.5,  3.0),
    'tp_multiplier':        (1.0,  8.0),
    'kc_multiplier':        (1.0,  4.0),
    'st_multiplier':        (1.0,  5.0),
    'supertrend_multiplier':(1.0,  5.0),
    # ── Bollinger Bands / Keltner ─────────────────────────────────────────────
    'bb_period':            (10,   50),
    'bb_std':               (1.0,  3.5),
    'bbw_sma_period':       (10,   50),
    'kc_window':            (10,   50),
    'kc_atr_window':        (5,    30),
    # ── VWAP ─────────────────────────────────────────────────────────────────
    'vwap_period':          (10,  100),
    'vwap_std_mult':        (0.5,  3.0),
    # ── Other indicators ─────────────────────────────────────────────────────
    'fvma_period':          (3,    20),
    'st_period':            (5,    30),
    'supertrend_length':    (5,    30),
    'zlema_period':         (5,    50),
    'zscore_period':        (20,  200),
    'zscore_threshold':     (0.5,  3.0),
    'z_period':             (10,  100),
    'z_threshold':          (0.5,  3.0),
    'aroon_period':         (10,   50),
    'aroon_threshold':      (50,   80),
    'mfi_period':           (5,    30),
    'wt_n1':                (5,    20),
    'wt_n2':                (10,   50),
    'wt_oversold':          (-80, -40),
    'wt_overbought':        (40,   80),
    'pivot_window':         (5,    30),
    'cvd_window':           (5,    50),
    'divergence_lookback':  (5,    30),
    'vol_lookback':         (5,    50),
    'vol_ma_period':        (5,    50),
    'vol_sma_period':       (5,    50),
    'intensity_period':     (5,    30),
    'intensity_std':        (1.0,  3.0),
    'pullback_lookback':    (2,    10),
    'swing_lookback':       (5,    30),
    'taker_threshold':      (0.5,  0.7),
    'taker_ratio_threshold':(0.5,  0.7),
    'taker_high_threshold': (0.5,  0.75),
    'taker_low_threshold':  (0.3,  0.55),
    'ob_volume_mult':       (1.0,  3.0),
    'fvg_min_pct':          (0.001,0.05),
    'min_gap_pct':          (0.001,0.05),
    # ── SL / TP / Hold ───────────────────────────────────────────────────────
    'sl_pct':               (0.01, 0.20),   # expanded — 5% cap was too tight for leveraged reversion
    'stop_loss_pct':        (0.01, 0.10),
    'take_profit_pct':      (0.02, 0.20),
    'tp_pct':               (0.01, 0.15),
    'tp_rr':                (1.0,  5.0),
    'tp_rr_ratio':          (1.0,  5.0),
    'rv_threshold':         (0.01, 0.10),
    'vol_threshold':        (0.5,  3.0),
    'vol_multiplier':       (1.0,  3.0),
    'deviation_pct':        (0.005,0.05),
    'ema_slope_thresh':     (0.0,  2.0),
    'sl_z_threshold':       (0.5,  3.0),
    'touch_band':           (0.001,0.02),
    'max_hold_bars':        (12,  200),
    'entry_window':         (1,    20),
    'peak_retrace_pct':     (0.3,  0.9),
    'retrace_depth':        (0.3,  0.9),
    'low_lookback':         (5,    50),
    # ── WAE ──────────────────────────────────────────────────────────────────
    'wae_sensitivity':      (50,  300),
    'wae_fast_len':         (5,    30),
    'wae_slow_len':         (20,   80),
    'wae_bb_len':           (10,   50),
    'wae_bb_mult':          (1.0,  3.0),
    'wae_deadzone':         (5,    50),
    # ── T3 / Stiff ────────────────────────────────────────────────────────────
    't3_length':            (5,    50),
    't3_vf':                (0.1,  1.0),
    'stiff_len':            (20,  100),
    'stiff_threshold':      (0.5,  1.0),
    # ── TII ──────────────────────────────────────────────────────────────────
    'tii_lower':            (20,   45),
    'tii_upper':            (55,   80),
    # ── Squeeze ──────────────────────────────────────────────────────────────
    'squeeze_period':       (10,   30),
}


STRATEGIES_DIR = os.path.join(ROOT_DIR, 'strategy_backtest', 'strategies')
SETTINGS_PATH  = os.path.join(ROOT_DIR, 'strategy_backtest', 'settings.py')


def _compute_score(sharpe, total_ret, norm_rf, pf_score, consistency_mult, trade_mult, roi_weight):
    """
    Blended objective score.
    roi_weight=0.0 → Sharpe-centric (original behaviour)
    roi_weight=0.5 → equal blend of Sharpe and log-ROI
    roi_weight=1.0 → pure log-ROI maximisation
    trade_mult     → 0-1 soft penalty applied when force_trade is on
    """
    # Cap at 500% so compounding exploits don't dwarf real Sharpe signal.
    _capped_ret  = math.copysign(min(abs(total_ret), 500.0), total_ret)
    ret_bonus    = 0.2 * math.copysign(math.log1p(abs(_capped_ret) / 100), _capped_ret)
    sharpe_score = (sharpe * 0.55) + (norm_rf * 0.20) + (pf_score * 0.15) + ret_bonus

    if roi_weight > 0:
        # log-ROI: 50%→0.69, 100%→1.10, 200%→1.61, 500%→2.30 — scale comparable to Sharpe
        roi_raw = math.copysign(math.log1p(abs(total_ret) / 25.0), total_ret)
        blended = (1.0 - roi_weight) * sharpe_score + roi_weight * roi_raw
    else:
        blended = sharpe_score

    return blended * consistency_mult * trade_mult


class _TradeTracker:
    """Tracks trial outcomes and auto-relaxes min_trades when Optuna is stuck."""
    def __init__(self, min_trades):
        self.min_trades  = min_trades
        self._failed     = 0
        self._total      = 0
        self._adaptations= 0

    def record(self, passed: bool):
        self._total += 1
        if not passed:
            self._failed += 1

    def maybe_relax(self):
        """Every 25 trials: if 85 %+ fail on trade count, halve the floor (max 2×)."""
        if self._total % 25 != 0 or self._adaptations >= 2 or self._total == 0:
            return
        fail_rate = self._failed / self._total
        if fail_rate >= 0.85:
            new_min = max(5, self.min_trades // 2)
            if new_min < self.min_trades:
                print(f'  [ADAPTIVE] {fail_rate:.0%} of trials failing trade floor — '
                      f'relaxing min_trades {self.min_trades}→{new_min}')
                self.min_trades   = new_min
                self._adaptations += 1


def update_strategy_file(class_name, best_params):
    """
    Find the strategy .py file by class name and update the __init__ default
    parameter values to the best params found by Optuna.
    Returns the path of the updated file, or None if not found.

    NOTE: ForgeStrategy is a generic multi-strategy wrapper — its constructor
    defaults are intentionally static placeholders. All real params are stored
    in settings.py. Skip file updates for this class to avoid corruption.
    """
    # ForgeStrategy: params live in settings.py only — never touch the file defaults.
    if class_name == 'ForgeStrategy':
        print(f'  [SKIP] ForgeStrategy — constructor defaults are static placeholders. '
              f'Params updated in settings.py only.')
        return None

    for fname in os.listdir(STRATEGIES_DIR):
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(STRATEGIES_DIR, fname)
        with open(fpath, 'r') as f:
            content = f.read()
        if f'class {class_name}' not in content:
            continue

        updated = content
        changed = []
        for param, value in best_params.items():
            if isinstance(value, float):
                val_str = str(round(value, 4))
                # Matches: param: float = 2.5  OR  param: Optional[float] = 2.5
                pattern = rf'(\b{re.escape(param)}\s*:[^=\n]*=\s*)[0-9]+\.?[0-9]*'
            elif isinstance(value, int):
                val_str = str(value)
                # Matches: param: int = 14
                pattern = rf'(\b{re.escape(param)}\s*:[^=\n]*=\s*)\d+'
            else:
                # Handle strings, e.g., '1h'
                val_str = f"'{value}'"
                # Matches: param: str = '1h' OR param: str = "1h"
                pattern = rf'(\b{re.escape(param)}\s*:[^=\n]*=\s*)["\']?[^"\',\s]+["\']?'
            new_content = re.sub(pattern, rf'\g<1>{val_str}', updated)
            if new_content != updated:
                changed.append(param)
                updated = new_content

        if updated != content:
            # Create backup before updating
            shutil.copy2(fpath, fpath + ".bak")
            with open(fpath, 'w') as f:
                f.write(updated)
            print(f'  [UPDATE] {fname} — updated defaults: {changed}')
            return fpath
        else:
            print(f'  [SKIP] {fname} — no matching __init__ params to update')
            return fpath  # file found but params may have different names
    return None


def update_settings_params(sid, best_params):
    """
    Update the 'params' dict for strategy ID sid inside settings.py.
    Scoped to the exact strategy block — won't touch other strategies.
    """
    with FileLock(SETTINGS_LOCK, timeout=120):
        return _update_settings_params_locked(sid, best_params)


def _update_settings_params_locked(sid, best_params):
    with open(SETTINGS_PATH, 'r') as f:
        content = f.read()

    # Find the start of this strategy's block: "sid": {
    sid_pattern = rf'["\']{{0,1}}{re.escape(str(sid))}\b["\']{{0,1}}\s*:\s*\{{'
    m = re.search(sid_pattern, content)
    if not m:
        print(f'  [WARN] Strategy ID {sid} not found in settings.py')
        return False

    start = m.start()

    # Find the end of this strategy block by counting braces
    depth, end = 0, start
    for i, ch in enumerate(content[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    block = content[start:end]
    changed = []

    for param, value in best_params.items():
        if isinstance(value, float):
            val_str = str(round(value, 4))
            pattern = rf'("{re.escape(param)}"\s*:\s*)[0-9]+\.?[0-9]*'
        elif isinstance(value, int):
            val_str = str(value)
            pattern = rf'("{re.escape(param)}"\s*:\s*)\d+'
        else:
            val_str = f'"{value}"'
            pattern = rf'("{re.escape(param)}"\s*:\s*)"[^"]*"'
        new_block = re.sub(pattern, rf'\g<1>{val_str}', block)
        if new_block != block:
            changed.append(f'{param}→{val_str}')
            block = new_block

    if block != content[start:end]:
        new_content = content[:start] + block + content[end:]
        # Guard: new file must not have fewer strategy IDs than current
        old_ids = set(re.findall(r'^\s{4}"(\d+)"\s*:\s*\{', content, re.MULTILINE))
        new_ids = set(re.findall(r'^\s{4}"(\d+)"\s*:\s*\{', new_content, re.MULTILINE))
        dropped = old_ids - new_ids
        if dropped:
            print(f'  [ABORT] settings.py write blocked — would drop IDs: {sorted(dropped, key=int)}')
            return False
        # Versioned backup: keep last 5 snapshots
        import glob, time
        snap_dir = os.path.join(os.path.dirname(SETTINGS_PATH), '.settings_snapshots')
        os.makedirs(snap_dir, exist_ok=True)
        snap = os.path.join(snap_dir, f'settings_{int(time.time())}.py')
        shutil.copy2(SETTINGS_PATH, snap)
        snaps = sorted(glob.glob(os.path.join(snap_dir, 'settings_*.py')))
        for old in snaps[:-5]:
            os.remove(old)
        shutil.copy2(SETTINGS_PATH, SETTINGS_PATH + ".bak")
        with open(SETTINGS_PATH, 'w') as f:
            f.write(new_content)
        print(f'  [UPDATE] settings.py ID={sid} — changed: {changed}')
        return True
    else:
        print(f'  [SKIP] settings.py ID={sid} — no param values changed')
        return False


def get_original_sharpe(sid):
    if not os.path.exists(SCAN_FILE):
        return None
    with open(SCAN_FILE) as f:
        scan = json.load(f)
    for r in scan.get('results', []):
        if str(r.get('id')) == str(sid):
            return r.get('sharpe')
    return None


def update_scan_results(sid, new_sharpe, new_return, new_dd, new_win_rate, new_trades, new_pf=None):
    """Write updated metrics back into scan_results.json for the given strategy ID."""
    with FileLock(SCAN_LOCK, timeout=120):
        _update_scan_results_locked(sid, new_sharpe, new_return, new_dd, new_win_rate, new_trades, new_pf)


def _update_scan_results_locked(sid, new_sharpe, new_return, new_dd, new_win_rate, new_trades, new_pf=None):
    if not os.path.exists(SCAN_FILE):
        return
    with open(SCAN_FILE) as f:
        scan = json.load(f)
    for r in scan.get('results', []):
        if str(r.get('id')) == str(sid):
            r['sharpe']        = new_sharpe
            r['total_return']  = new_return
            r['max_drawdown']  = new_dd
            r['win_rate']      = new_win_rate
            r['total_trades']  = new_trades
            if new_pf is not None:
                r['profit_factor'] = new_pf

            # Apply BAD override rules from tuner_specs.md BEFORE checking Sharpe
            bad_reasons = []
            if new_pf is not None and new_pf < 1.0:
                bad_reasons.append(f'PF={new_pf} < 1.0')
            if new_return < 0:
                bad_reasons.append(f'negative total return ({new_return}%)')
            if new_dd > 70:
                bad_reasons.append(f'MDD={new_dd}% > 70%')
            if new_trades < 30:
                bad_reasons.append(f'only {new_trades} trades (below 30 CLT minimum)')

            if bad_reasons:
                r['grade'] = 'BAD'
                r['grade_reason'] = f'Fine-tuned but BAD override: {"; ".join(bad_reasons)}'
            elif new_sharpe >= 1.0 and new_trades >= 100:
                r['grade'] = 'GOOD'
                r['grade_reason'] = f'Fine-tuned — Sharpe {new_sharpe}, {new_trades} trades'
            elif new_sharpe >= 0.3:
                r['grade'] = 'MEDIOCRE'
                trades_note = f' — only {new_trades} trades, statistically thin' if new_trades < 100 else ''
                r['grade_reason'] = f'Fine-tuned — Sharpe {new_sharpe}{trades_note}'
            else:
                r['grade'] = 'BAD'
                r['grade_reason'] = f'Fine-tuned but Sharpe {new_sharpe} still below 0.3'
            break
    # Recalculate top-level grade counts so dashboard summary stays accurate
    counts = {'GOOD': 0, 'MEDIOCRE': 0, 'BAD': 0, 'PENDING': 0, 'ERROR': 0}
    for r in scan.get('results', []):
        g = r.get('grade', 'PENDING')
        if g in counts:
            counts[g] += 1
    scan.update(counts)
    # Mark as classified if no PENDING entries remain
    if counts['PENDING'] == 0:
        scan['classified'] = True

    with open(SCAN_FILE, 'w') as f:
        json.dump(scan, f, indent=2)
    good, mediocre, bad = counts['GOOD'], counts['MEDIOCRE'], counts['BAD']
    print(f'  [UPDATE] scan_results.json — ID={sid} Sharpe={new_sharpe} | Counts: GOOD={good} MEDIOCRE={mediocre} BAD={bad}')


def run_finetune(strategy_id, n_trials=None, date_from='2023-01-01', date_to='2026-12-31',
                 no_update=False, force_trade=False, roi_weight=0.0, min_trades=None):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    from strategy_backtest.settings     import STRATEGY_LIBRARY
    from strategy_backtest.engine       import BacktestEngine
    from strategy_backtest.risk         import RiskManager
    from strategy_backtest.metrics      import compute_metrics, _extract_numeric
    from strategy_backtest.run_backtest import load_data
    import strategy_backtest.strategies as strat_reg

    sid = str(strategy_id)
    if sid not in STRATEGY_LIBRARY:
        print(f'[ERROR] Strategy ID {sid} not found in STRATEGY_LIBRARY')
        sys.exit(1)

    cfg = STRATEGY_LIBRARY[sid]
    strat_cls = getattr(strat_reg, cfg['class'], None)
    if strat_cls is None:
        print(f'[ERROR] Class {cfg["class"]} not found in strategies module')
        sys.exit(1)

    # Always use the strategy's own configured full period so Optuna and the
    # final result are on the same data — no train/test split confusion.
    date_from = cfg['data'].get('date_from', date_from)
    date_to   = cfg['data'].get('date_to',   date_to)

    # Merge default ranges with strategy-specific overrides
    ranges = dict(DEFAULT_RANGES)
    # Track which params have custom hard bounds — auto-expand must not cross these
    custom_hard_bounds = {}
    if hasattr(strat_cls, 'OPTIMIZATION_RANGES'):
        ranges.update(strat_cls.OPTIMIZATION_RANGES)
        custom_hard_bounds = dict(strat_cls.OPTIMIZATION_RANGES)
        print(f"  [INFO] Strategy {cfg['class']} has custom OPTIMIZATION_RANGES. Overriding defaults.")

    # Auto-scale trials by number of tunable dims if not explicitly passed
    base_params_temp = cfg.get('params', {})
    n_tunable = len([k for k in base_params_temp if k in ranges])
    # Auto-scale trials: floor of 100, or 25 per dimension
    auto_scaled = max(100, n_tunable * 25)
    
    if n_trials is None:
        n_trials = auto_scaled
    else:
        # User/Agent provided a number; still enforce the 100 floor for quality
        if n_trials < 100:
            print(f'  [INFO] Enforcing minimum of 100 trials (requested {n_trials}).')
            n_trials = max(100, n_trials)

    print(f'Fine-tuning ID={sid} {cfg["class"]} ({cfg["data"].get("coins","?")} / {cfg["data"].get("timeframes","?")})')
    print(f'Period: {date_from} → {date_to}  |  Trials: {n_trials}  |  Tunable params: {n_tunable}\n')

    df = load_data(cfg['data']['coins'], cfg['data']['timeframes'], date_from, date_to)
    if df is None or df.empty or len(df) < 50:
        print('[ERROR] Insufficient data for this strategy')
        sys.exit(1)

    base_params = cfg.get('params', {})

    n_days = (df.index[-1] - df.index[0]).days
    # Default floor: 30 (CLT minimum for statistical validity).
    # Caller can pass min_trades to raise this for high-frequency strategies.
    min_trades_required = int(min_trades) if min_trades is not None else 30

    # Strategy-level override (add MIN_TRADES = N to strategy class to control floor)
    if hasattr(strat_cls, 'MIN_TRADES'):
        min_trades_required = int(strat_cls.MIN_TRADES)
        print(f'  [INFO] Strategy-level MIN_TRADES override: {min_trades_required}')

    roi_weight = float(max(0.0, min(1.0, roi_weight)))
    if force_trade:
        print(f'  [MODE] force_trade=ON  — soft trade penalty, absolute floor=5')
    if roi_weight > 0:
        print(f'  [MODE] roi_weight={roi_weight:.2f} — {"balanced Sharpe+ROI" if roi_weight < 1.0 else "pure ROI"} scoring')

    # Enhancement 1: fresh baseline — run current params through the engine so
    # worth_saving compares against what the strategy actually does TODAY, not a
    # potentially stale scan_results.json entry (which may have used different params).
    baseline_sharpe = None
    try:
        _rm_base = RiskManager(
            risk_per_trade=cfg['risk']['risk_per_trade'],
            leverage=cfg['risk']['leverage'],
            trading_fee=cfg['risk']['trading_fee'],
            slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
            maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
        )
        _eng_base = BacktestEngine(
            df, strat_cls(df, **base_params), _rm_base,
            initial_balance=cfg['risk']['initial_balance']
        )
        _eq_base = _eng_base.run()
        if _eq_base and len(_eq_base) >= 2:
            _m_base  = compute_metrics(_eq_base, cfg['risk']['initial_balance'],
                                       timestamps=_eng_base.df.index, trades=_eng_base.trades)
            _nm_base = _extract_numeric(_m_base)
            _base_trades = int(_nm_base.get('Total Trades', 0))
            if _base_trades >= min_trades_required:
                baseline_sharpe = round(float(_nm_base.get('Sharpe Ratio', -999)), 3)
                print(f'Baseline (current params): Sharpe={baseline_sharpe}  Trades={_base_trades}')
            else:
                print(f'Baseline: only {_base_trades} trades (< {min_trades_required}) — falling back to scan Sharpe')
                baseline_sharpe = get_original_sharpe(sid)
    except Exception as _e:
        print(f'Baseline run failed ({_e}) — falling back to scan Sharpe')
        baseline_sharpe = get_original_sharpe(sid)

    # Determine which params to tune (only those present in base_params AND in ranges)
    tunable = {k: v for k, v in base_params.items() if k in ranges}
    fixed   = {k: v for k, v in base_params.items() if k not in ranges}

    if not tunable:
        print('[WARN] No tunable parameters found — using all base params as fixed, running objective only')

    n_dims = len(tunable)
    n_startup = max(25, n_dims * 4)   # enough random exploration before TPE kicks in

    _tt = _TradeTracker(min_trades_required)  # adaptive min-trades relaxation

    def objective(trial):
        trial_params = dict(fixed)
        for k, v in tunable.items():
            r = ranges[k]
            if isinstance(r, list):
                trial_params[k] = trial.suggest_categorical(k, r)
            elif isinstance(v, int):
                lo, hi = r
                trial_params[k] = trial.suggest_int(k, int(lo), int(hi))
            else:
                lo, hi = r
                trial_params[k] = trial.suggest_float(k, float(lo), float(hi))
        try:
            # Let strategy reject degenerate param combos early
            if not strat_cls.validate_params(trial_params):
                return -999.0

            rm = RiskManager(
                risk_per_trade=cfg['risk']['risk_per_trade'],
                leverage=cfg['risk']['leverage'],
                trading_fee=cfg['risk']['trading_fee'],
                slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
                maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
            )
            engine = BacktestEngine(
                df, strat_cls(df, **trial_params), rm,
                initial_balance=cfg['risk']['initial_balance']
            )
            equity = engine.run()
            if not equity or len(equity) < 2:
                return -999.0
            m = compute_metrics(equity, cfg['risk']['initial_balance'],
                                timestamps=engine.df.index, trades=engine.trades)
            nm = _extract_numeric(m)
            sharpe    = float(nm.get('Sharpe Ratio',  -999) or -999)
            total_ret = float(nm.get('Total Return',  -999) or -999)
            mdd       = abs(float(nm.get('Max Drawdown %', 100) or 100))
            trades    = int(nm.get('Total Trades',    0))

            log_to_agent('crypto-strategy-tuner',
                         f"FINETUNING | Strategy {sid} | Trial {trial.number} | "
                         f"Sharpe: {sharpe:.3f} | Return: {total_ret:.1f}% | Trades: {trades}")

            # ── Hard guards (always enforced) ─────────────────────────────────
            if total_ret < -90: return -999.0  # catastrophic loss
            if mdd > 70:        return -999.0  # Enhancement 3: MDD hard cap

            # ── Trade count guard (hard or soft depending on force_trade) ─────
            # _tt.maybe_relax()
            effective_min = _tt.min_trades
            trade_ok = trades >= effective_min

            if force_trade:
                if trades < 5: return -999.0   # absolute floor regardless
                trade_mult = min(1.0, (trades / effective_min) ** 0.5)
            else:
                _tt.record(trade_ok)
                if not trade_ok: return -999.0
                trade_mult = 1.0

            # ── Consistency guard ─────────────────────────────────────────────
            trade_df = pd.DataFrame(engine.trades)
            if not trade_df.empty:
                # Filter to entry events only (BUY/SELL); engine.trades key is 'time'
                entry_df = trade_df[trade_df['type'].isin(['BUY', 'SELL'])].copy()
                if not entry_df.empty:
                    entry_df['time'] = pd.to_datetime(entry_df['time'])
                    trades_per_year = entry_df.set_index('time').resample('YE').size()
                    active_years    = (trades_per_year >= 3).sum()
                    total_years     = len(pd.date_range(engine.df.index[0], engine.df.index[-1], freq='YE'))
                    consistency_mult= min(1.0, active_years / (total_years * 0.6)) if total_years > 1 else 1.0
                else:
                    consistency_mult = 0.0
            else:
                consistency_mult = 0.0

            # ── Profit Factor ─────────────────────────────────────────────────
            pf_raw    = nm.get('Profit Factor', 0)
            pf_is_inf = pf_raw is None or (isinstance(pf_raw, (int, float)) and float(pf_raw) >= 99)
            pf        = 2.0 if pf_is_inf else float(pf_raw or 0)
            pf_score  = max(-1.0, min(2.0, pf - 1.0))
            norm_rf   = max(-5.0, min(5.0, (total_ret / mdd) / 2.0)) if mdd > 0 else 0

            return _compute_score(sharpe, total_ret, norm_rf, pf_score,
                                  consistency_mult, trade_mult, roi_weight)
        except Exception:
            return -999.0

    sampler = optuna.samplers.TPESampler(n_startup_trials=n_startup, seed=42)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    # Reconstruct best params
    best_params = dict(fixed)
    for k, v in tunable.items():
        best_params[k] = study.best_params.get(k, v)

    # --- AUTOMATED RANGE EXPANSION ---
    needs_expansion = False
    expanded_ranges = dict(ranges)
    
    for k in tunable:
        r = ranges[k]
        if isinstance(r, list): continue
            
        lo, hi = r
        val = best_params[k]
        span = hi - lo
        if span > 0:
            # If hit ceiling, expand high bound by 50% of span
            if abs(val - hi) <= (span * 0.01) or val >= hi:
                expanded_ranges[k] = (lo, hi + (span * 0.5))
                needs_expansion = True
                print(f"  [AUTO-EXPAND] {k} hit CEILING. Expanding range to {expanded_ranges[k]}")
            # If hit floor, expand low bound by 50% of span (if non-negative logic applies)
            # Never expand below a custom hard floor set in OPTIMIZATION_RANGES
            elif abs(val - lo) <= (span * 0.01) or val <= lo:
                hard_floor = custom_hard_bounds[k][0] if k in custom_hard_bounds else None
                # For positive-valued ranges, never expand below half the original floor —
                # prevents ATR multipliers and similar physical params reaching near-zero.
                if lo > 0:
                    natural_floor = lo / 2.0
                    new_lo = max(natural_floor, lo - (span * 0.5))
                else:
                    new_lo = max(0 if lo >= 0 else -9999, lo - (span * 0.5))
                if hard_floor is not None:
                    new_lo = max(new_lo, hard_floor)  # never cross the custom minimum
                if new_lo < lo:
                    expanded_ranges[k] = (new_lo, hi)
                    needs_expansion = True
                    print(f"  [AUTO-EXPAND] {k} hit FLOOR. Expanding range to {expanded_ranges[k]}")
                else:
                    print(f"  [HARD-FLOOR] {k} hit FLOOR but custom minimum {hard_floor} blocks expansion.")

    if needs_expansion:
        print("  [RE-OPTIMIZE] Rerunning with expanded boundaries for deeper peak discovery...")
        # Recursively call once with expanded ranges (manual expansion to avoid complex recursion logic)
        # We replace the local ranges with expanded ones and run a second smaller study
        def objective_expanded(trial):
            trial_params = dict(fixed)
            for k, v in tunable.items():
                r = expanded_ranges[k]
                if isinstance(r, list):
                    trial_params[k] = trial.suggest_categorical(k, r)
                elif isinstance(v, int):
                    lo, hi = r
                    trial_params[k] = trial.suggest_int(k, int(lo), int(hi))
                else:
                    lo, hi = r
                    trial_params[k] = trial.suggest_float(k, float(lo), float(hi))
            try:
                if not strat_cls.validate_params(trial_params):
                    return -999.0
                rm = RiskManager(risk_per_trade=cfg['risk']['risk_per_trade'], leverage=cfg['risk']['leverage'],
                                 trading_fee=cfg['risk']['trading_fee'], slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
                                 maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'])
                engine = BacktestEngine(df, strat_cls(df, **trial_params), rm, initial_balance=cfg['risk']['initial_balance'])
                equity = engine.run()
                m  = compute_metrics(equity, cfg['risk']['initial_balance'], timestamps=engine.df.index, trades=engine.trades)
                nm = _extract_numeric(m)
                sharpe    = float(nm.get('Sharpe Ratio', -999))
                total_ret = float(nm.get('Total Return', -999))
                mdd       = abs(float(nm.get('Max Drawdown %', 100)))
                trades    = int(nm.get('Total Trades', 0))
                if total_ret < -90: return -999.0
                if mdd > 70:        return -999.0
                eff_min = _tt.min_trades
                if force_trade:
                    if trades < 5: return -999.0
                    t_mult = min(1.0, (trades / eff_min) ** 0.5)
                else:
                    if trades < eff_min: return -999.0
                    t_mult = 1.0
                norm_rf  = max(-5.0, min(5.0, (total_ret / mdd) / 2.0)) if mdd > 0 else 0
                pf_raw   = nm.get('Profit Factor', 0)
                pf_is_inf = pf_raw is None or (isinstance(pf_raw, (int, float)) and float(pf_raw) >= 99)
                pf        = 2.0 if pf_is_inf else float(pf_raw or 0)
                pf_score  = max(-1.0, min(2.0, pf - 1.0))
                return _compute_score(sharpe, total_ret, norm_rf, pf_score, 1.0, t_mult, roi_weight)
            except Exception: return -999.0

        study_exp = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=42))
        study_exp.optimize(objective_expanded, n_trials=int(n_trials * 0.5), show_progress_bar=False)
        
        if study_exp.best_value > study.best_value:
            print(f"  [SUCCESS] Found superior peak in expanded range (Score: {study_exp.best_value:.3f} vs {study.best_value:.3f})")
            for k, v in tunable.items():
                best_params[k] = study_exp.best_params.get(k, v)
        else:
            print("  [INFO] Expanded search did not find better results. Keeping original peak.")

    # Final backtest with best params on the same full-period df
    rm = RiskManager(
        risk_per_trade=cfg['risk']['risk_per_trade'],
        leverage=cfg['risk']['leverage'],
        trading_fee=cfg['risk']['trading_fee'],
        slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
        maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
    )
    engine = BacktestEngine(
        df, strat_cls(df, **best_params), rm,
        initial_balance=cfg['risk']['initial_balance']
    )
    equity = engine.run()
    m  = compute_metrics(equity, cfg['risk']['initial_balance'],
                         timestamps=engine.df.index, trades=engine.trades)
    nm = _extract_numeric(m)

    original_sharpe = get_original_sharpe(sid)   # kept for logging/result record only
    best_sharpe     = round(study.best_value, 3)
    full_sharpe     = round(nm.get('Sharpe Ratio', best_sharpe), 3)
    full_return     = round(nm.get('Total Return',   0), 1)
    full_dd         = round(nm.get('Max Drawdown %', 0), 1)
    full_win_rate   = round(nm.get('Win Rate',       0), 1)
    full_trades     = int(nm.get('Total Trades',     0))
    full_pf         = round(nm.get('Profit Factor',  0), 2)

    compare_sharpe = baseline_sharpe if baseline_sharpe is not None else original_sharpe
    # When force_trade is on, only enforce an absolute floor of 5 for saving
    effective_min = 5 if force_trade else _tt.min_trades

    if roi_weight >= 0.5:
        # ROI-dominant mode: save if return improved (or no baseline) and passes trade floor
        orig_return   = None
        if os.path.exists(SCAN_FILE):
            with open(SCAN_FILE) as _f:
                _scan = json.load(_f)
            for _r in _scan.get('results', []):
                if str(_r.get('id')) == sid:
                    orig_return = _r.get('total_return')
                    break
        worth_saving = (orig_return is None or full_return > orig_return) and full_trades >= effective_min
        print(f'\nBaseline Return : {orig_return}%  |  Best Return: {full_return}%  (roi_weight={roi_weight:.2f})')
    else:
        worth_saving = (compare_sharpe is None or full_sharpe > compare_sharpe) and full_trades >= effective_min
        print(f'\nBaseline Sharpe : {compare_sharpe}  (scan: {original_sharpe})')

    print(f'Best Sharpe     : {full_sharpe}  |  Best Return: {full_return}%  |  Trades: {full_trades}')
    print(f'Worth saving    : {worth_saving}')
    if force_trade and full_trades < min_trades_required:
        print(f'  [FORCE_TRADE] {full_trades} trades below original floor ({min_trades_required}) — saved anyway')
    print(f'Best params     : {best_params}')

    # Check for boundary hits (if optimal value is at the edge of the range)
    boundary_warnings = []
    for k in tunable:
        r = ranges[k]
        if isinstance(r, list):
            continue  # Boundaries don't apply to categorical switches
            
        lo, hi = r
        val = best_params[k]
        # Threshold: equal to bound or within 0.5% of the range span
        span = hi - lo
        if span > 0:
            if abs(val - hi) <= (span * 0.005) or val >= hi:
                boundary_warnings.append(f"  [⚠] {k} hit CEILING ({val} near {hi})")
            elif abs(val - lo) <= (span * 0.005) or val <= lo:
                boundary_warnings.append(f"  [⚠] {k} hit FLOOR ({val} near {lo})")
    
    if boundary_warnings:
        print("\nBOUNDARY WARNINGS (Optimal value may be outside current range):")
        for w in boundary_warnings:
            print(w)
        print("Suggestion: Expand OPTIMIZATION_RANGES for these parameters in the strategy file.")

    strategy_file_updated = None
    settings_updated      = False

    if worth_saving and not no_update:
        print('\n[AUTO-UPDATE] Meets threshold — writing best params to source files...')
        strategy_file_updated = update_strategy_file(cfg['class'], best_params)
        settings_updated      = update_settings_params(sid, best_params)
        if strategy_file_updated:
            print(f'  Strategy file : {os.path.relpath(strategy_file_updated, ROOT_DIR)}')
        if settings_updated:
            print(f'  settings.py   : params for ID={sid} updated')

        # Update scan_results.json so Phase 6 tuner tab shows fresh numbers
        update_scan_results(sid, full_sharpe, full_return, full_dd, full_win_rate, full_trades, full_pf)
    elif worth_saving and no_update:
        print('\n[REPORT ONLY] Optimization complete. Code updates skipped due to no_update flag.')
    else:
        print('\n[SKIP UPDATE] Below threshold — original params kept in source files.')

    result = {
        'strategy_id':          sid,
        'class':                cfg['class'],
        'coin':                 cfg['data'].get('coins', '?'),
        'tf':                   cfg['data'].get('timeframes', '?'),
        'date_from':            date_from,
        'date_to':              date_to,
        'original_params':      base_params,
        'best_params':          best_params,
        'original_sharpe':      original_sharpe,
        'best_sharpe':          full_sharpe,
        'total_return':         full_return,
        'max_drawdown':         full_dd,
        'win_rate':             full_win_rate,
        'total_trades':         full_trades,
        'n_trials':             n_trials,
        'force_trade':          force_trade,
        'roi_weight':           roi_weight,
        'worth_saving':         worth_saving,
        'strategy_file_updated': os.path.relpath(strategy_file_updated, ROOT_DIR) if strategy_file_updated else None,
        'settings_updated':     settings_updated,
        'finetuned_at':         datetime.now().isoformat(),
    }

    # Save to finetune_results.json
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    existing = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []
    existing = [r for r in existing if str(r.get('strategy_id')) != sid]
    existing.append(result)
    with open(RESULT_FILE, 'w') as f:
        json.dump(existing, f, indent=2)

    print(f'\nResults saved to {RESULT_FILE}')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fine-tune a strategy with Optuna')
    parser.add_argument('--strategy_id', required=True, help='Numeric strategy ID from STRATEGY_LIBRARY')
    parser.add_argument('--trials',      type=int,   default=None,
                        help='Optuna trials (default: auto-scaled to max(100, n_tunable_params × 25))')
    parser.add_argument('--date_from',   default='2023-01-01')
    parser.add_argument('--date_to',     default='2026-12-31')
    parser.add_argument('--no_update',   action='store_true',
                        help='Report best params only, do NOT update code or settings.')
    parser.add_argument('--force_trade', action='store_true',
                        help='Use soft trade penalty instead of hard cutoff — helps strategies '
                             'with very few baseline trades (e.g. divergence, divergence patterns).')
    parser.add_argument('--roi_weight',  type=float, default=0.0,
                        help='0.0=Sharpe-centric (default), 0.5=balanced Sharpe+ROI, 1.0=pure ROI maximisation.')
    parser.add_argument('--min_trades',  type=int,   default=None,
                        help='Hard minimum trades per trial (default: 30). Raise for high-frequency strategies.')
    args = parser.parse_args()
    run_finetune(args.strategy_id, args.trials, args.date_from, args.date_to,
                 args.no_update, args.force_trade, args.roi_weight, args.min_trades)
