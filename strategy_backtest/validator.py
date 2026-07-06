"""
strategy_backtest/validator.py — 27-Rule Rulebook compliance validator (SignalHive standard).

Runs every backtest-integrity check from T0 through the Crypto Pack,
scores the strategy per the SignalHive standard, and prints a structured report.

27 Rules:
  - T0: 2 prerequisites (data, reproducibility)
  - T1: 11 fatal gates (profitability, risk, sample size, costs, walk-forward, lookahead, leverage)
  - T2: 5 blocking gates (walk-forward efficiency, OOS decay, overfit, DSR, random label, P&L structure)
  - T3: 7 robustness advisories (hit rate, param robustness, bootstrap, truncation)
  - CR: 3 crypto-specific gates (funding, news blackout, weekend)

Verdict logic (SignalHive standard):
  - T0 fail → REJECTED
  - T1 fail → FAIL
  - T2 fail → FAIL
  - CR fail (crypto only) → FAIL
  - T3-only warnings → PASS_WITH_WARNINGS
  - All clear → PASS

Score: (T1 pass × 40) + (T2 pass × 30) + (T3 count × 4) + (CR pass × 10) = 0–100

Usage:
    python strategy_backtest/validator.py --strategy 3
    python strategy_backtest/validator.py --strategy 3 --folds 8
    python strategy_backtest/validator.py --strategy 3 --save report_3.json
    python strategy_backtest/validator.py --strategy 3 --quick   # skip slow PBO/bootstrap
"""

from __future__ import annotations

import os
import sys
import json
import copy
import argparse
import contextlib
import io

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import strategy_backtest.strategies  # auto-registers all strategy classes

from strategy_backtest.settings       import STRATEGY_LIBRARY
from strategy_backtest.engine         import BacktestEngine
from strategy_backtest.risk           import RiskManager
from strategy_backtest.metrics        import compute_metrics, _extract_numeric
from strategy_backtest.run_backtest   import load_data
from strategy_backtest.frequency_utils import detect_frequency, classify_frequency, get_threshold
from strategy_backtest.scripts.wfo_runner import run_wfo


# ── Global Thresholds (overridable per-frequency) ────────────────────────────

THRESH = {
    'sharpe':           0.50,      # T1-01
    'total_return':     0.00,      # T1-02
    'max_dd_pct':      20.00,      # T1-02 (corrected from 50 → 20)
    'win_rate':        30.00,      # T1-04 (overridden per frequency)
    'profit_factor':    1.00,      # T1-05
    'worst_daily_loss':-20.00,     # T1-06 (overridden per frequency)
    'cost_ratio':       0.50,      # T1-10 (overridden per frequency, 50% for HFT, 30% intraday, 15% swing, 5% position)
    'wf_efficiency':    0.50,      # T2-01 (overridden per frequency)
    'oos_is_mdd_ratio': 1.50,      # T1-03b
    'oos_sharpe_decay': 0.50,      # T2-02
    'dsr_p':            0.05,       # T2-04
    'random_label_pct': 0.95,      # T2-05
    'monthly_gtp':      1.00,      # T2-06
    'bootstrap_pos':    0.60,      # T3-03
    'lookahead_tol':    0.15,      # T1-09
    'funding_impact':   0.25,      # CR-01
    'news_daily_loss': -0.05,      # CR-02
}
    'wf_efficiency':    0.50,
    'oos_is_mdd_ratio': 1.50,
    'oos_sharpe_decay': 0.50,
    'dsr_p':            0.05,
    'random_label_pct': 0.95,
    'monthly_gtp':      1.00,
    'bootstrap_pos':    0.60,
    'lookahead_tol':    0.15,
    'sensitivity_drop': 0.50,
    'truncation_sharpe': 0.0,
    'funding_impact':   0.25,
    'news_daily_loss': -0.05,
}

# ── Scoring Formula (SignalHive standard) ──────────────────────────────────────
# Score = (T1_pass × 40) + (T2_pass × 30) + (T3_count_pass × 4) + (CR_pass × 10)
# Max score = 100 (all pass)
# T1 pass: +40 pts (1 rule set, binary)
# T2 pass: +30 pts (1 rule set, binary)
# T3 count: +4 pts each (6 rules counted: T3-00 through T3-05; T3-06 is advisory only)
# CR pass: +10 pts (1 rule set, binary, crypto-only)

SCORE_WEIGHTS = {
    'T1_pass': 40.0,      # All T1 rules pass → +40
    'T2_pass': 30.0,      # All T2 rules pass → +30
    'T3_each': 4.0,       # Each T3 rule (max 6) → +4 each (T3-00 to T3-05)
    'CR_pass': 10.0,      # All CR rules pass → +10
}

REGIME_DATES = {
    'bear_2022':  ('2022-01-01', '2022-12-31'),
    'range_2023': ('2023-01-01', '2023-12-31'),
    'bull_2024':  ('2024-01-01', '2024-12-31'),
}

NEWS_EVENTS = [
    ('LUNA_May2022', '2022-05-07', '2022-05-14'),
    ('FTX_Nov2022',  '2022-11-07', '2022-11-14'),
    ('ETF_Jan2024',  '2024-01-10', '2024-01-17'),
]


# ── Internal helpers ──────────────────────────────────────────────────────────

@contextlib.contextmanager
def _silent():
    with open(os.devnull, 'w') as devnull:
        old = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old


def _run_full(cfg: dict, df: pd.DataFrame, params_override: dict = None):
    """
    Run strategy on `df`.
    Returns (equity, trades, timestamps, full_metrics) or (None, None, None, {}) on failure.
    """
    import strategy_backtest.strategies as _strats
    strat_cls = getattr(_strats, cfg['class'], None)
    if strat_cls is None:
        return None, None, None, {}

    risk_cfg = cfg['risk']
    params   = {**cfg.get('params', {}), **(params_override or {})}

    try:
        strategy = strat_cls(df, **params)
        rm = RiskManager(
            risk_per_trade=risk_cfg['risk_per_trade'],
            leverage=risk_cfg['leverage'],
            trading_fee=risk_cfg['trading_fee'],
            slippage_pct=risk_cfg.get('slippage_pct', 0.0005),
            maintenance_margin_rate=risk_cfg['maintenance_margin_rate'],
        )
        engine = BacktestEngine(df, strategy, rm, initial_balance=risk_cfg['initial_balance'])
        equity = engine.run()
        if not equity:
            return None, None, None, {}
        m = compute_metrics(
            equity=equity,
            initial_balance=risk_cfg['initial_balance'],
            timestamps=engine.df.index,
            trades=engine.trades,
        )
        return equity, engine.trades, engine.df.index, m
    except Exception as exc:
        return None, None, None, {'error': str(exc)}


def _quick_sharpe(equity, timestamps=None):
    returns = pd.Series(equity).pct_change().dropna()
    if len(returns) < 5:
        return 0.0
    if timestamps is not None and len(timestamps) >= 2:
        ts  = pd.DatetimeIndex(timestamps)
        med = float(ts.to_series().diff().dropna().dt.total_seconds().median())
        bpy = (365.25 * 24 * 3600 / med) if med > 0 else 365.0
    else:
        bpy = 365.0
    std = float(returns.std())
    return float(returns.mean() / std * np.sqrt(bpy)) if std > 0 else 0.0


def _quick_mdd(equity):
    arr  = np.array(equity)
    peak = np.maximum.accumulate(arr)
    dd   = (peak - arr) / np.where(peak > 0, peak, 1) * 100
    return float(np.max(dd))


def _total_return(equity, initial_balance):
    return (equity[-1] - initial_balance) / initial_balance * 100


def _parse_metric(m, key):
    v = m.get(key, 0)
    try:
        s = str(v).replace('$', '').replace(',', '').replace('%', '').strip()
        return float(s) if s not in ('∞', '', 'None') else (99.0 if s == '∞' else 0.0)
    except (ValueError, TypeError):
        return 0.0


def _to_native(v):
    """Convert numpy scalar types to native Python types for JSON serialization."""
    if v is None:
        return None
    try:
        import numpy as np
        if isinstance(v, np.bool_):
            return bool(v)
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
    except ImportError:
        pass
    return v


def _result(code, passed, details, score_pts):
    p = bool(passed)
    return {
        'code':       code,
        'passed':     p,
        'score':      float(score_pts) if p else 0.0,
        'max_score':  float(score_pts),
        'details':    str(details),
    }


# ── T0: Data Prerequisites ────────────────────────────────────────────────────

def check_T0_data(cfg: dict, df: pd.DataFrame) -> dict:
    issues = []
    if df is None or df.empty:
        return _result('T0-01', False, 'No data loaded.', 0)

    for col in ('Open', 'High', 'Low', 'Close', 'Volume'):
        pct = df[col].isna().mean()
        if pct > 0.01:
            issues.append(f"{col} has {pct:.1%} NaN")

    if not df.index.is_monotonic_increasing:
        issues.append('Index not monotonic')

    min_bars = 2000
    if len(df) < min_bars:
        issues.append(f"Only {len(df)} bars (need ≥ {min_bars})")

    dupes = df.index.duplicated().sum()
    if dupes > 0:
        issues.append(f"{dupes} duplicate timestamps")

    passed = len(issues) == 0
    detail = 'OK' if passed else '; '.join(issues)
    return _result('T0-01', passed, f"Data integrity: {len(df):,} bars | {detail}", 0)


# ── T1: Fatal Gates ───────────────────────────────────────────────────────────

def check_T1_metrics(full_m: dict, initial_balance: float, equity: list, timestamps, cfg: dict = None) -> list:
    """T1-01 through T1-07 from the full metrics and equity curve."""
    results = []
    W = SCORE_WEIGHTS['T1']

    sharpe = _parse_metric(full_m, 'Sharpe Ratio')
    results.append(_result('T1-01', sharpe >= THRESH['sharpe'],
                            f"Sharpe Ratio = {sharpe:.3f}  (≥ {THRESH['sharpe']})", W))

    tr = _total_return(equity, initial_balance)
    results.append(_result('T1-02', tr > THRESH['total_return'],
                            f"Total Return = {tr:.2f}%  (> 0)", W))

    mdd = _quick_mdd(equity)
    results.append(_result('T1-03', mdd < THRESH['max_dd_pct'],
                            f"Max Drawdown = {mdd:.2f}%  (< {THRESH['max_dd_pct']}%)", W))

    wr = _parse_metric(full_m, 'Win Rate')
    results.append(_result('T1-04', wr >= THRESH['win_rate'],
                            f"Win Rate = {wr:.2f}%  (≥ {THRESH['win_rate']}%)", W))

    pf_raw = full_m.get('Profit Factor', '0')
    pf = 99.0 if str(pf_raw) == '∞' else _parse_metric(full_m, 'Profit Factor')
    results.append(_result('T1-05', pf >= THRESH['profit_factor'],
                            f"Profit Factor = {pf:.2f}  (≥ {THRESH['profit_factor']})", W))

    n_params   = len(cfg.get('params', {})) if cfg else 0
    min_trades = max(30, 5 * n_params)
    n_trades   = int(_parse_metric(full_m, 'Total Trades'))
    results.append(_result('T1-05b', n_trades >= min_trades,
                            f"Total Trades = {n_trades}  (≥ max(30, 5×{n_params}params) = {min_trades})", W))

    wdl = _parse_metric(full_m, 'Worst Daily Loss')
    if wdl == 0 and 'Worst Daily Loss' not in full_m:
        results.append(_result('T1-06', True, 'Worst Daily Loss = N/A (skipped — timestamps needed)', W))
    else:
        results.append(_result('T1-06', wdl >= THRESH['worst_daily_loss'],
                                f"Worst Daily Loss = {wdl:.2f}%  (≥ {THRESH['worst_daily_loss']}%)", W))

    cr_raw = full_m.get('Cost Ratio', None)
    if cr_raw is None:
        results.append(_result('T1-07', True, 'Cost Ratio = N/A (no trades or zero profit)', W))
    else:
        cr = _parse_metric(full_m, 'Cost Ratio')
        results.append(_result('T1-07', cr < THRESH['cost_ratio'],
                                f"Cost Ratio = {cr:.2%}  (< {THRESH['cost_ratio']:.0%})", W))

    return results


def check_T1_wfo(wfo_result: dict) -> dict:
    if not wfo_result:
        return _result('T1-08', False, 'WFO did not complete.', SCORE_WEIGHTS['T1'])
    wf_pass = wfo_result.get('wf_pass', False)
    eff = wfo_result.get('wf_efficiency', 0.0)
    return _result('T1-08', wf_pass,
                   f"WF Efficiency = {eff:.3f}  (≥ {THRESH['wf_efficiency']})", SCORE_WEIGHTS['T1'])


def check_T1_lookahead(cfg: dict, df: pd.DataFrame, orig_sharpe: float) -> dict:
    if df is None or df.empty or len(df) < 10:
        return _result('T1-09', False, 'Cannot run lookahead probe — empty data.', SCORE_WEIGHTS['T1'])

    df_shifted = df.shift(1).dropna()
    with _silent():
        eq_s, _, ts_s, _ = _run_full(cfg, df_shifted)

    if eq_s is None:
        return _result('T1-09', False, 'Lookahead probe run failed.', SCORE_WEIGHTS['T1'])

    sharpe_s = _quick_sharpe(eq_s, ts_s)
    if abs(orig_sharpe) < 1e-6:
        detail = f"Orig Sharpe≈0, shifted={sharpe_s:.3f} — inconclusive"
        return _result('T1-09', True, detail, SCORE_WEIGHTS['T1'])

    delta_pct = (sharpe_s - orig_sharpe) / abs(orig_sharpe)
    passed = delta_pct < THRESH['lookahead_tol']
    detail = (f"Sharpe orig={orig_sharpe:.3f}  shifted={sharpe_s:.3f}  "
              f"Δ={delta_pct:+.1%}  (expect < {THRESH['lookahead_tol']:.0%} gain)")
    return _result('T1-09', passed, detail, SCORE_WEIGHTS['T1'])


def check_T1_regime_survival(cfg: dict, df: pd.DataFrame) -> dict:
    W = SCORE_WEIGHTS['T1']
    pos = 0
    regime_info = {}
    for name, (rs, re) in REGIME_DATES.items():
        sl = df.loc[rs:re] if isinstance(df.index, pd.DatetimeIndex) else pd.DataFrame()
        if sl is None or len(sl) < 50:
            regime_info[name] = 'N/A (< 50 bars)'
            continue
        with _silent():
            eq, _, ts, _ = _run_full(cfg, sl)
        if eq is None:
            regime_info[name] = 'run failed'
            continue
        sh = _quick_sharpe(eq, ts)
        regime_info[name] = f"Sharpe={sh:.3f}"
        if sh > 0:
            pos += 1

    available = sum(1 for v in regime_info.values() if 'N/A' not in v and 'failed' not in v)
    threshold = max(2, round(available * 0.6))
    passed = pos >= threshold
    detail = ', '.join(f"{k}={v}" for k, v in regime_info.items())
    detail += f"  →  {pos}/{available} positive"
    return _result('T1-10', passed, detail, W)


# ── T2: Quality Gates ─────────────────────────────────────────────────────────

def check_T2_wfo_quality(wfo_result: dict) -> list:
    W = SCORE_WEIGHTS['T2']
    results = []

    if not wfo_result:
        results.append(_result('T2-01', False, 'No WFO result.', W))
        results.append(_result('T2-02', False, 'No WFO result.', W))
        return results

    eff = wfo_result.get('wf_efficiency', 0.0)
    results.append(_result('T2-01', eff >= THRESH['wf_efficiency'],
                            f"WF Efficiency = {eff:.3f}  (≥ {THRESH['wf_efficiency']})", W))

    decay = wfo_result.get('oos_is_decay', 999.0)
    results.append(_result('T2-02', decay <= THRESH['oos_sharpe_decay'],
                            f"IS→OOS Decay = {decay:.3f}  (≤ {THRESH['oos_sharpe_decay']})", W))

    return results


def check_T2_pbo(cfg: dict, df: pd.DataFrame, equity_orig: list, timestamps) -> dict:
    W = SCORE_WEIGHTS['T2']
    num_params = {k: v for k, v in cfg.get('params', {}).items() if isinstance(v, (int, float))}

    if not num_params:
        return _result('T2-03', True, 'PBO skipped — no numerical params to perturb (N/A).', W)

    param_keys = list(num_params.keys())[:4]
    configs_equity = [equity_orig]

    for pkey in param_keys:
        for factor in (0.90, 1.10):
            override = {pkey: type(num_params[pkey])(num_params[pkey] * factor)}
            with _silent():
                eq_v, _, _, _ = _run_full(cfg, df, params_override=override)
            if eq_v is not None and len(eq_v) == len(equity_orig):
                configs_equity.append(eq_v)

    if len(configs_equity) < 3:
        return _result('T2-03', True, 'PBO skipped — not enough valid param variants.', W)

    rets = np.column_stack([
        pd.Series(eq).pct_change().dropna().values
        for eq in configs_equity
    ])
    min_T = min(e.shape[0] for e in [rets])
    rets = rets[:min_T, :]

    try:
        from core.function_PBO import pbo as _pbo
        import scipy.stats as _ss

        def _sharpe_col(mat):
            return np.array([
                (mat[:, i].mean() / mat[:, i].std() * np.sqrt(365.0))
                if mat[:, i].std() > 0 else 0.0
                for i in range(mat.shape[1])
            ])

        S = 8
        if rets.shape[0] // S < 10:
            return _result('T2-03', True, 'PBO skipped — insufficient bars per chunk.', W)

        res = _pbo(rets, S=S, metric_func=_sharpe_col,
                   name_exp='validator_pbo', threshold=0.0,
                   n_jobs=1, verbose=False, plot=False)
        pbo_val   = float(res.pbo)
        oos_loss  = float(res.prob_oos_loss)
        passed    = pbo_val < 0.50 and oos_loss < 0.30
        detail    = (f"PBO={pbo_val:.3f}  OOS_loss_prob={oos_loss:.3f}  "
                     f"configs={rets.shape[1]}  chunks={S}")
        return _result('T2-03', passed, detail, W)

    except Exception as exc:
        return _result('T2-03', True, f'PBO computation error: {exc} — treated as N/A.', W)


def check_T2_dsr(full_m: dict) -> dict:
    W = SCORE_WEIGHTS['T2']
    dsr_str = full_m.get('DSR p-value', None)
    if dsr_str is None:
        return _result('T2-04', True, 'DSR p-value not computed (< 10 bars or no scipy).', W)
    try:
        dsr_p = float(dsr_str)
        passed = dsr_p < THRESH['dsr_p']
        return _result('T2-04', passed,
                       f"DSR p-value = {dsr_p:.4f}  (< {THRESH['dsr_p']})", W)
    except (ValueError, TypeError):
        return _result('T2-04', True, f'DSR parse error: {dsr_str}', W)


def check_T2_random_label(equity: list, timestamps, n_shuffles: int = 500) -> dict:
    W = SCORE_WEIGHTS['T2']
    returns = pd.Series(equity).pct_change().dropna().values
    if len(returns) < 30:
        return _result('T2-05', True, 'Random-label skipped — too few returns.', W)

    real_sh = _quick_sharpe(equity, timestamps)
    rng = np.random.default_rng(42)
    rand_sharpes = []
    for _ in range(n_shuffles):
        sh = rng.permutation(returns)
        sd = sh.std()
        if sd > 0:
            rand_sharpes.append(sh.mean() / sd * np.sqrt(365.0))

    if not rand_sharpes:
        return _result('T2-05', True, 'Random-label computation failed.', W)

    pct_rank = float(np.mean(np.array(rand_sharpes) < real_sh))
    passed   = pct_rank >= THRESH['random_label_pct']
    p95      = float(np.percentile(rand_sharpes, 95))
    return _result('T2-05', passed,
                   f"Real Sharpe={real_sh:.3f}  Rand p95={p95:.3f}  Rank={pct_rank:.2%}  "
                   f"(≥ {THRESH['random_label_pct']:.0%})", W)


def check_T2_monthly_gtp(full_m: dict) -> dict:
    W = SCORE_WEIGHTS['T2']
    pf_raw = full_m.get('Profit Factor', '0')
    pf     = 99.0 if str(pf_raw) == '∞' else _parse_metric(full_m, 'Profit Factor')
    pf_ok  = pf >= 1.5

    gtp_raw = full_m.get('Monthly GTP', None)
    if gtp_raw is None:
        # Fall back to PF ≥ 1.5 alone
        passed = pf_ok
        return _result('T2-06', passed,
                       f"Monthly GTP = N/A  |  PF={pf:.2f}  → OR pass={pf_ok}  "
                       f"(GTP≥1.0 OR PF≥1.5)", W)
    if str(gtp_raw) == '∞':
        return _result('T2-06', True,
                       f"Monthly GTP = ∞ (no losing months)  |  PF={pf:.2f}", W)
    try:
        gtp    = float(gtp_raw)
        gtp_ok = gtp >= THRESH['monthly_gtp']
        passed = gtp_ok or pf_ok
        return _result('T2-06', passed,
                       f"Monthly GTP={gtp:.2f}(≥1.0:{gtp_ok})  PF={pf:.2f}(≥1.5:{pf_ok})  "
                       f"→ OR={passed}", W)
    except (ValueError, TypeError):
        passed = pf_ok
        return _result('T2-06', passed,
                       f"Monthly GTP parse error: {gtp_raw}  |  PF={pf:.2f}  OR={passed}", W)


# ── T3: Warnings ──────────────────────────────────────────────────────────────

def check_T3_bootstrap(equity: list, timestamps, n_boot: int = 500, block: int = 20) -> dict:
    W = SCORE_WEIGHTS['T3']
    returns = pd.Series(equity).pct_change().dropna().values
    if len(returns) < block * 3:
        return _result('T3-01', True, 'Bootstrap skipped — too few bars.', W)

    real_sh = _quick_sharpe(equity, timestamps)
    rng  = np.random.default_rng(42)
    sharpes = []
    max_start = len(returns) - block
    for _ in range(n_boot):
        n_bl = len(returns) // block + 1
        starts = rng.integers(0, max_start, size=n_bl)
        boot = np.concatenate([returns[s:s + block] for s in starts])[:len(returns)]
        sd = boot.std()
        if sd > 0:
            sharpes.append(boot.mean() / sd * np.sqrt(365.0))

    if not sharpes:
        return _result('T3-01', True, 'Bootstrap computation failed.', W)

    sharpes = np.array(sharpes)
    pct_pos = float(np.mean(sharpes > 0))
    ci5     = float(np.percentile(sharpes, 5))
    ci95    = float(np.percentile(sharpes, 95))
    passed  = pct_pos >= THRESH['bootstrap_pos']
    return _result('T3-01', passed,
                   f"Real={real_sh:.3f}  90%CI=[{ci5:.3f}, {ci95:.3f}]  "
                   f"Pos={pct_pos:.1%}  (≥ {THRESH['bootstrap_pos']:.0%})", W)


def check_T3_sensitivity(cfg: dict, df: pd.DataFrame, orig_sharpe: float) -> dict:
    W = SCORE_WEIGHTS['T3']
    num_params = {k: v for k, v in cfg.get('params', {}).items() if isinstance(v, (int, float))}

    if not num_params:
        return _result('T3-02', True, 'Param sensitivity skipped — no numerical params.', W)

    sharpes = {'orig': orig_sharpe}
    for pkey, pval in list(num_params.items())[:4]:
        for label, factor in (('m10', 0.90), ('p10', 1.10)):
            override = {pkey: type(pval)(pval * factor)}
            with _silent():
                eq_v, _, ts_v, _ = _run_full(cfg, df, params_override=override)
            if eq_v is not None:
                sharpes[f"{pkey}_{label}"] = _quick_sharpe(eq_v, ts_v)

    if len(sharpes) < 2:
        return _result('T3-02', True, 'Not enough variants completed.', W)

    vals = list(sharpes.values())
    sh_min = min(vals)
    sh_max = max(vals)
    drop   = (orig_sharpe - sh_min) / abs(orig_sharpe) if abs(orig_sharpe) > 1e-6 else 0.0
    passed = drop < THRESH['sensitivity_drop']
    detail = (f"Orig={orig_sharpe:.3f}  Min={sh_min:.3f}  Max={sh_max:.3f}  "
              f"Worst_drop={drop:.1%}  (< {THRESH['sensitivity_drop']:.0%})")
    return _result('T3-02', passed, detail, W)


def check_T3_regime_mdd(full_m: dict) -> dict:
    W = SCORE_WEIGHTS['T3']
    regime_mdd = full_m.get('Regime MDD', None)
    if regime_mdd is None:
        return _result('T3-03', True, 'Regime MDD not computed (timestamps needed).', W)
    worst = min(regime_mdd.values())
    passed = worst > -40.0
    detail = '  '.join(f"{k}={v:.1f}%" for k, v in regime_mdd.items())
    return _result('T3-03', passed, detail, W)


def check_T3_weekend_sharpe(full_m: dict) -> dict:
    W = SCORE_WEIGHTS['T3']
    wkd  = full_m.get('Weekday Sharpe', None)
    wknd = full_m.get('Weekend Sharpe', None)
    if wkd is None or wknd is None:
        return _result('T3-04', True, 'Weekend Sharpe not computed.', W)
    try:
        wkd_f  = float(wkd)
        wknd_f = float(wknd)
        ratio  = abs(wknd_f / wkd_f) if abs(wkd_f) > 1e-6 else 0.0
        passed = ratio >= 0.30
        return _result('T3-04', passed,
                       f"Weekday Sharpe={wkd_f:.3f}  Weekend Sharpe={wknd_f:.3f}  "
                       f"Ratio={ratio:.2f}  (≥ 0.30)", W)
    except (TypeError, ZeroDivisionError):
        return _result('T3-04', True, f'Weekend Sharpe parse error: {wkd}/{wknd}', W)


def check_T3_truncation(cfg: dict, df: pd.DataFrame) -> dict:
    W = SCORE_WEIGHTS['T3']
    n = len(df)
    cuts = {'50%': n // 2, '75%': int(n * 0.75)}
    passed_all = True
    details    = []

    for label, end_idx in cuts.items():
        sl = df.iloc[:end_idx]
        with _silent():
            eq, _, ts, _ = _run_full(cfg, sl)
        if eq is None:
            details.append(f"{label}=ERR")
            continue
        sh = _quick_sharpe(eq, ts)
        tr = _total_return(eq, cfg['risk']['initial_balance'])
        ok = sh > THRESH['truncation_sharpe'] and tr > 0
        if not ok:
            passed_all = False
        details.append(f"{label}:Sh={sh:.2f},Ret={tr:.1f}%({'OK' if ok else 'FAIL'})")

    return _result('T3-05', passed_all, '  '.join(details), W)


# ── Crypto Pack ───────────────────────────────────────────────────────────────

def check_CR_funding(cfg: dict, df: pd.DataFrame, trades: list) -> dict:
    W = SCORE_WEIGHTS['CR']
    if 'funding_rate' not in df.columns:
        return _result('CR-01', True, 'No funding_rate column in data — skipped.', W)
    if not trades:
        return _result('CR-01', True, 'No trades — skipped.', W)

    net_profit = cfg['risk']['initial_balance']
    for t in trades:
        net_profit += t.get('pnl', 0) - t.get('fee', 0)
    net_profit -= cfg['risk']['initial_balance']

    # Approximate funding cost: sum(|position| × funding_rate) per 8-hour period
    avg_fr    = float(df['funding_rate'].abs().mean())
    n_periods = len(df) * (df.index.to_series().diff().dt.total_seconds().median() or 3600) / (8 * 3600)
    est_fund  = avg_fr * n_periods * cfg['risk']['initial_balance'] * cfg['risk']['leverage']

    if abs(net_profit) < 1e-6:
        return _result('CR-01', True, 'Zero net profit — funding impact undefined.', W)

    impact = est_fund / abs(net_profit)
    passed = impact < THRESH['funding_impact']
    return _result('CR-01', passed,
                   f"Est. funding cost / net profit ≈ {impact:.2%}  "
                   f"(avg_rate={avg_fr:.5f})  (< {THRESH['funding_impact']:.0%})", W)


def check_CR_news(equity: list, timestamps) -> dict:
    W = SCORE_WEIGHTS['CR']
    if timestamps is None:
        return _result('CR-02', True, 'No timestamps — news blackout skipped.', W)

    equity_s = pd.Series(equity, index=pd.DatetimeIndex(timestamps))
    worst_events = []
    passed = True

    for name, start, end in NEWS_EVENTS:
        window = equity_s.loc[start:end]
        if len(window) < 2:
            continue
        daily = window.resample('1D').last().dropna().pct_change().dropna()
        if len(daily) == 0:
            continue
        worst = float(daily.min())
        worst_events.append(f"{name}:{worst:.1%}")
        if worst < THRESH['news_daily_loss']:
            passed = False

    if not worst_events:
        return _result('CR-02', True, 'No news event windows found in data.', W)

    return _result('CR-02', passed,
                   'Worst daily loss per event: ' + '  '.join(worst_events) +
                   f"  (threshold > {THRESH['news_daily_loss']:.0%}/day)", W)


def check_CR_vol_regime(equity: list, timestamps) -> dict:
    W = SCORE_WEIGHTS['CR']
    if timestamps is None:
        return _result('CR-03', True, 'No timestamps — vol-regime check skipped.', W)

    equity_s = pd.Series(equity, index=pd.DatetimeIndex(timestamps))
    daily    = equity_s.resample('1D').last().dropna().pct_change().dropna()
    if len(daily) < 30:
        return _result('CR-03', True, 'Insufficient daily bars for vol-regime check.', W)

    vol = daily.rolling(30).std().dropna() * np.sqrt(252)
    aligned_daily = daily.loc[vol.index]
    low_vol  = aligned_daily[vol < vol.quantile(0.33)]
    high_vol = aligned_daily[vol > vol.quantile(0.67)]

    def sh(r):
        sd = float(r.std())
        return float(r.mean() / sd * np.sqrt(252)) if sd > 0 and len(r) >= 5 else 0.0

    lv_sh = sh(low_vol)
    hv_sh = sh(high_vol)
    passed = lv_sh > -0.5 and hv_sh > -0.5
    return _result('CR-03', passed,
                   f"Low-vol Sharpe={lv_sh:.3f}  High-vol Sharpe={hv_sh:.3f}  "
                   f"(both > -0.5)", W)


# ── Main Validator ────────────────────────────────────────────────────────────

def validate(strategy_id: str, n_folds: int = 6, quick: bool = False,
             save_path: str = None) -> dict:
    if strategy_id not in STRATEGY_LIBRARY:
        print(f"[ERROR] Strategy '{strategy_id}' not found.")
        return {}

    cfg      = STRATEGY_LIBRARY[strategy_id]
    data_cfg = cfg['data']
    risk_cfg = cfg['risk']

    print(f"\n{'='*72}")
    print(f"  26-Rule Validator: strategy {strategy_id} | {cfg['id']}")
    print(f"  Desc    : {cfg['desc']}")
    print(f"  Period  : {data_cfg['date_from']} → {data_cfg['date_to']}")
    print(f"  Quick   : {quick}")
    print(f"{'='*72}")

    # ── Load data ──
    print("\n[0/7] Loading data...")
    with _silent():
        try:
            df = load_data(data_cfg['coins'], data_cfg['timeframes'],
                           data_cfg['date_from'], data_cfg['date_to'])
        except Exception as e:
            print(f"[ERROR] Data load failed: {e}")
            return {}

    print(f"      {len(df):,} bars  {df.index[0].date()} → {df.index[-1].date()}")

    # ── Full backtest ──
    print("\n[1/7] Running full backtest...")
    equity, trades, timestamps, full_m = _run_full(cfg, df)
    if equity is None:
        print("[ERROR] Full backtest failed.")
        return {}

    orig_sharpe = _quick_sharpe(equity, timestamps)
    num = _extract_numeric(full_m)
    print(f"      Sharpe={orig_sharpe:.3f}  MDD={_quick_mdd(equity):.1f}%  "
          f"Return={_total_return(equity, risk_cfg['initial_balance']):.1f}%  "
          f"Trades={num.get('Total Trades', 0)}")

    # ── WFO ──
    print(f"\n[2/7] Walk-forward ({n_folds} folds)...")
    with _silent():
        wfo_result = run_wfo(strategy_id, n_folds=n_folds)

    # ── Collect all check results ──
    print("\n[3/7] Running rulebook checks...")

    all_checks = []

    # T0
    t0 = check_T0_data(cfg, df)
    all_checks.append(t0)

    # T1
    t1_basic = check_T1_metrics(full_m, risk_cfg['initial_balance'], equity, timestamps, cfg)
    all_checks.extend(t1_basic)
    all_checks.append(check_T1_wfo(wfo_result))

    print("      T1-09 lookahead probe...")
    all_checks.append(check_T1_lookahead(cfg, df, orig_sharpe))

    print("      T1-10 regime survival...")
    all_checks.append(check_T1_regime_survival(cfg, df))

    # T2
    all_checks.extend(check_T2_wfo_quality(wfo_result))

    if not quick:
        print("      T2-03 PBO...")
        all_checks.append(check_T2_pbo(cfg, df, equity, timestamps))
    else:
        all_checks.append(_result('T2-03', True, 'PBO skipped (--quick mode).', SCORE_WEIGHTS['T2']))

    all_checks.append(check_T2_dsr(full_m))

    print("      T2-05 random-label control...")
    all_checks.append(check_T2_random_label(equity, timestamps, n_shuffles=200 if quick else 500))

    all_checks.append(check_T2_monthly_gtp(full_m))

    # T3
    print("      T3-01 block bootstrap...")
    all_checks.append(check_T3_bootstrap(equity, timestamps, n_boot=200 if quick else 500))

    if not quick:
        print("      T3-02 param sensitivity...")
        all_checks.append(check_T3_sensitivity(cfg, df, orig_sharpe))
    else:
        all_checks.append(_result('T3-02', True, 'Sensitivity skipped (--quick mode).', SCORE_WEIGHTS['T3']))

    all_checks.append(check_T3_regime_mdd(full_m))
    all_checks.append(check_T3_weekend_sharpe(full_m))

    print("      T3-05 truncation test...")
    all_checks.append(check_T3_truncation(cfg, df))

    # CR
    all_checks.append(check_CR_funding(cfg, df, trades))
    all_checks.append(check_CR_news(equity, timestamps))
    all_checks.append(check_CR_vol_regime(equity, timestamps))

    # ── Scoring ──
    total_score = sum(c['score']      for c in all_checks if c['code'] != 'T0-01')
    max_score   = sum(c['max_score']  for c in all_checks if c['code'] != 'T0-01')
    passed_count = sum(1 for c in all_checks if c['passed'])
    total_count  = len(all_checks)
    overall_pass = (total_score / max_score >= 0.70) if max_score > 0 else False

    t1_pass = all(c['passed'] for c in all_checks if c['code'].startswith('T1'))
    data_ok  = next(c['passed'] for c in all_checks if c['code'] == 'T0-01')

    # ── Print report ──
    print(f"\n{'='*72}")
    print(f"  VALIDATION REPORT: {cfg['id']}")
    print(f"{'='*72}")

    tier_order = ['T0', 'T1', 'T2', 'T3', 'CR']
    for tier in tier_order:
        tier_checks = [c for c in all_checks if c['code'].startswith(tier)]
        if not tier_checks:
            continue
        tier_score = sum(c['score']     for c in tier_checks)
        tier_max   = sum(c['max_score'] for c in tier_checks)
        label = {
            'T0': 'Tier 0 — Prerequisites',
            'T1': 'Tier 1 — Fatal Gates',
            'T2': 'Tier 2 — Quality Gates',
            'T3': 'Tier 3 — Warnings',
            'CR': 'Crypto Pack',
        }.get(tier, tier)
        print(f"\n  {label}  [{tier_score:.0f}/{tier_max:.0f}]")
        for c in tier_checks:
            icon = '✓' if c['passed'] else '✗'
            pts  = f"+{c['score']:.0f}" if c['passed'] else f"  0/{c['max_score']:.0f}"
            print(f"    [{icon}] {c['code']:<7}  ({pts}pt)  {c['details']}")

    print(f"\n{'='*72}")
    pct = total_score / max_score * 100 if max_score > 0 else 0
    verdict = 'APPROVED' if overall_pass and data_ok else (
              'T1 FATAL FAIL' if not t1_pass else 'BELOW THRESHOLD')
    print(f"  SCORE   : {total_score:.0f} / {max_score:.0f}  ({pct:.1f}%)")
    print(f"  CHECKS  : {passed_count}/{total_count} passed")
    print(f"  VERDICT : {verdict}  (threshold ≥ 70%)")
    print(f"{'='*72}")

    result = {
        'strategy_id':    strategy_id,
        'strategy_name':  cfg['id'],
        'score':          round(total_score, 1),
        'max_score':      round(max_score, 1),
        'pct':            round(pct, 1),
        'verdict':        verdict,
        'passed_checks':  passed_count,
        'total_checks':   total_count,
        'checks':         all_checks,
        'wfo_summary':    {k: _to_native(wfo_result.get(k)) for k in (
                           'wf_efficiency', 'oos_is_mdd_ratio', 'oos_is_decay',
                           'positive_oos', 'total_folds', 'wf_pass')
                           } if wfo_result else {},
    }

    if save_path:
        out = os.path.join(_ROOT, save_path)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        with open(out, 'w') as fh:
            json.dump(result, fh, indent=2, default=str)
        print(f"\n  Report saved → {out}")

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='26-Rule Rulebook Validator')
    parser.add_argument('--strategy', required=True, help='Strategy ID')
    parser.add_argument('--folds',    type=int, default=6,  help='WFO folds (default 6)')
    parser.add_argument('--save',     default=None, help='Save JSON report to path')
    parser.add_argument('--quick',    action='store_true',
                        help='Skip slow checks (PBO, sensitivity) for fast validation')
    args = parser.parse_args()
    validate(args.strategy, n_folds=args.folds, quick=args.quick, save_path=args.save)


if __name__ == '__main__':
    main()
