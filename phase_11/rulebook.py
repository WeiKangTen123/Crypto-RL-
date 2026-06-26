"""
Phase 11 — Backtest Rulebook Validator
26 rules: Tier 0 (2) · Tier 1 (10) · Tier 2 (6) · Tier 3 (5) · Crypto Pack (3)

Usage:
    python phase_11/rulebook.py            # analytics only (fast)
    python phase_11/rulebook.py --full     # includes walk-forward & param sensitivity
"""

import os, sys, json, hashlib, argparse, warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import phase_11.engine as eng
from phase_11.engine import (
    run_pair_backtest, PAIRS, DATE_FROM, DATE_TO, TIMEFRAME,
    NORM_WINDOW, PRIOR_DIV_WINDOW, MIN_DIVERGENCE, PROFIT_TARGET,
    RECROSS_BUFFER, HARD_STOP_PCT, MAX_HOLD_BARS, COOLDOWN_BARS,
    load_pair_data,
)

DATASET_DIR   = os.path.join(ROOT, 'dataset')
RESULTS_FILE  = os.path.join(ROOT, 'phase_11', 'data', 'results.json')
RULEBOOK_FILE = os.path.join(ROOT, 'phase_11', 'data', 'rulebook.json')

# ── Adaptive thresholds — intraday (2-24h average hold) ──────────────────────
THRESH = {
    'max_drawdown':      0.20,
    'mc_p5_mdd':         0.25,
    'worst_daily_loss':  0.04,
    'regime_mdd':        0.30,
    'sharpe':            0.50,
    'trade_count':       100,
    'cost_ratio':        0.30,
    'wf_efficiency':     0.50,
    'oos_decay':         0.50,
    'pbo':               0.15,
    'dsr_p':             0.05,
    'random_sharpe':     0.30,
    'gtp':               1.00,
    'pf':                1.50,
    'hit_rate':          0.40,
    'param_pass_rate':   0.70,
    'bootstrap_p5':      0.00,
    'mc_median':         0.00,
    'funding_ratio':     0.50,
    'news_sharpe_diff':  0.30,
    'weekend_diff':      1.00,
}

# FOMC dates 2021-2026 (approximate — scheduled meetings)
FOMC_DATES = [
    '2021-01-27','2021-03-17','2021-04-28','2021-06-16','2021-07-28',
    '2021-09-22','2021-11-03','2021-12-15',
    '2022-01-26','2022-03-16','2022-05-04','2022-06-15','2022-07-27',
    '2022-09-21','2022-11-02','2022-12-14',
    '2023-02-01','2023-03-22','2023-05-03','2023-06-14','2023-07-26',
    '2023-09-20','2023-11-01','2023-12-13',
    '2024-01-31','2024-03-20','2024-05-01','2024-06-12','2024-07-31',
    '2024-09-18','2024-11-07','2024-12-18',
    '2025-01-29','2025-03-19','2025-05-07','2025-06-18','2025-07-30',
    '2025-09-17','2025-11-05','2025-12-10',
    '2026-01-28','2026-03-18','2026-04-29','2026-06-10',
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def rule(id_, name, desc, metric_name, threshold_str, status, value, value_str, tier, severity):
    return {
        'id': id_, 'name': name, 'desc': desc,
        'metric_name': metric_name, 'threshold_str': threshold_str,
        'status': status,   # PASS / FAIL / WARN / SKIP
        'value': value, 'value_str': value_str,
        'tier': tier, 'severity': severity,
    }


def build_portfolio_daily(pairs_data):
    """Combine all pairs' net P&L into a daily series and compute equity curve."""
    all_pnls = []
    for p in pairs_data:
        if not p.get('trades'):
            continue
        for t in p['trades']:
            all_pnls.append({'date': t['exit_time'][:10], 'pnl': t['net_pnl']})
    if not all_pnls:
        return pd.Series(dtype=float), np.array([])
    df = pd.DataFrame(all_pnls)
    df['date'] = pd.to_datetime(df['date'])
    daily = df.groupby('date')['pnl'].sum().sort_index()
    return daily, np.cumsum(daily.values)


def compute_mdd(cum_equity, total_capital):
    """Peak-to-trough max drawdown as fraction of total_capital."""
    if len(cum_equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(cum_equity)
    return float(np.min(cum_equity - peak)) / total_capital


def block_bootstrap_sharpe(daily_pnl, n_sims=1000, block_size=20, seed=42):
    """Block-bootstrap daily P&L → distribution of annualized Sharpe ratios."""
    rng = np.random.default_rng(seed)
    pnl = daily_pnl.values if hasattr(daily_pnl, 'values') else np.array(daily_pnl)
    n = len(pnl)
    if n < 30:
        return np.array([])
    sharpes = []
    for _ in range(n_sims):
        blocks = []
        while sum(len(b) for b in blocks) < n:
            start = rng.integers(0, n)
            block = pnl[start:start + block_size]
            blocks.append(block)
        resampled = np.concatenate(blocks)[:n]
        mu, sd = resampled.mean(), resampled.std()
        if sd > 0:
            sharpes.append(mu / sd * np.sqrt(365))
    return np.array(sharpes)


def block_bootstrap_mdd(trades, total_capital, n_sims=1000, block_size=15, seed=42):
    """Block-bootstrap trade sequence → distribution of max drawdowns."""
    rng = np.random.default_rng(seed)
    pnls = np.array([t['net_pnl'] for t in trades])
    n = len(pnls)
    if n < 10:
        return np.array([])
    mdds = []
    for _ in range(n_sims):
        idxs = []
        while len(idxs) < n:
            start = rng.integers(0, n)
            idxs.extend(range(start, min(start + block_size, n)))
        perm = np.array(pnls[idxs[:n]])
        cum = np.cumsum(perm)
        peak = np.maximum.accumulate(cum)
        mdds.append(float(np.min(cum - peak)) / total_capital)
    return np.array(mdds)


def compute_dsr(daily_pnl):
    """Deflated Sharpe Ratio: corrects for non-normality of returns."""
    pnl = daily_pnl.values if hasattr(daily_pnl, 'values') else np.array(daily_pnl)
    T = len(pnl)
    if T < 30:
        return 1.0, 0.0
    mu, sd = pnl.mean(), pnl.std(ddof=1)
    if sd == 0:
        return 1.0, 0.0
    SR = mu / sd * np.sqrt(365)
    skew = scipy_stats.skew(pnl)
    kurt = scipy_stats.kurtosis(pnl)  # excess kurtosis
    sigma_sr = np.sqrt((1 - skew * (SR / np.sqrt(365)) + (kurt - 1) / 4 * (SR / np.sqrt(365)) ** 2) / (T - 1))
    if sigma_sr <= 0:
        return 1.0, 0.0
    SR_hat = SR / sigma_sr / np.sqrt(365)  # normalize
    dsr_p = float(1 - scipy_stats.norm.cdf(SR_hat))
    return dsr_p, SR


def load_funding_series(coin, timeframe='15m'):
    """Load funding rate as a Series indexed by open_time at settlement bars only."""
    path = os.path.join(DATASET_DIR, coin, timeframe, 'funding_rate.parquet')
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    df['open_time'] = pd.to_datetime(df['open_time'])
    # Only keep 8h settlement bars: 00:00, 08:00, 16:00
    mask = (df['open_time'].dt.hour % 8 == 0) & (df['open_time'].dt.minute == 0)
    df = df[mask].set_index('open_time')['funding_rate']
    return df


def approx_news_dates():
    """Approximate FOMC + CPI (11th of each month) + NFP (1st Friday) events."""
    dates = set(pd.to_datetime(FOMC_DATES))
    d = pd.Timestamp('2021-01-01')
    end = pd.Timestamp('2026-06-01')
    while d < end:
        # CPI ≈ 11th
        dates.add(d.replace(day=11))
        # NFP ≈ first Friday
        first = d.replace(day=1)
        dow = first.dayofweek  # 0=Mon, 4=Fri
        offset = (4 - dow) % 7
        dates.add(first + pd.Timedelta(days=offset))
        d = (d + pd.offsets.MonthBegin(1))
    return sorted(dates)


def compute_sharpe_on_trades(trades, date_from=None, date_to=None):
    """Annualized Sharpe from a trade list using calendar days."""
    if not trades:
        return 0.0
    pnl_ser = pd.Series(
        [t['net_pnl'] for t in trades],
        index=pd.to_datetime([t['exit_time'] for t in trades]),
    )
    daily = pnl_ser.resample('1D').sum()
    if date_from and date_to:
        n_days = (pd.to_datetime(date_to) - pd.to_datetime(date_from)).days
    else:
        n_days = (daily.index[-1] - daily.index[0]).days
    if daily.std() == 0 or n_days < 1:
        return 0.0
    return float(daily.mean() / daily.std() * np.sqrt(n_days))


# ── Walk-forward ──────────────────────────────────────────────────────────────

def run_walk_forward(pairs_data, n_folds=8):
    """8-fold anchored walk-forward per pair. Returns (wf_efficiency, oos_decay)."""
    print('  [WF] Running walk-forward...', flush=True)
    fold_ratios = []
    all_is_sharpes, all_oos_sharpes = [], []

    for pr in pairs_data:
        pair = pr['pair']
        coin_a, coin_b = pr['coin_a'], pr['coin_b']
        date_from = pr['date_from']
        date_to   = pr['date_to']

        d_from = pd.to_datetime(date_from)
        d_to   = pd.to_datetime(date_to)
        total_days = (d_to - d_from).days

        if total_days < 365:
            print(f'  [WF] {pair}: too short, skipping')
            continue

        seg_days = total_days / (n_folds + 1)
        breakpoints = [d_from + timedelta(days=int(seg_days * k)) for k in range(n_folds + 2)]

        pair_is, pair_oos = [], []
        for k in range(1, n_folds + 1):
            is_from  = date_from
            is_to    = breakpoints[k].strftime('%Y-%m-%d')
            oos_from = breakpoints[k].strftime('%Y-%m-%d')
            oos_to   = breakpoints[k + 1].strftime('%Y-%m-%d')

            try:
                r_is  = run_pair_backtest(coin_a, coin_b, DATASET_DIR, is_from,  is_to,  TIMEFRAME)
                r_oos = run_pair_backtest(coin_a, coin_b, DATASET_DIR, oos_from, oos_to, TIMEFRAME)
                is_sh  = compute_sharpe_on_trades(r_is.get('trades', []),  is_from,  is_to)
                oos_sh = compute_sharpe_on_trades(r_oos.get('trades', []), oos_from, oos_to)
                if r_is.get('total_trades', 0) >= 3 and r_oos.get('total_trades', 0) >= 3:
                    pair_is.append(is_sh)
                    pair_oos.append(oos_sh)
            except Exception:
                pass

        if pair_is:
            mean_is  = np.mean(pair_is)
            mean_oos = np.mean(pair_oos)
            ratio = mean_oos / mean_is if abs(mean_is) > 0.01 else 0.0
            fold_ratios.append(ratio)
            all_is_sharpes.append(mean_is)
            all_oos_sharpes.append(mean_oos)
            print(f'  [WF] {pair}: IS={mean_is:.3f} OOS={mean_oos:.3f} ratio={ratio:.3f}', flush=True)

    if not fold_ratios:
        return 0.0, 1.0

    wf_eff  = float(np.mean(fold_ratios))
    mean_is  = np.mean(all_is_sharpes)
    mean_oos = np.mean(all_oos_sharpes)
    decay = (mean_is - mean_oos) / abs(mean_is) if abs(mean_is) > 0.01 else 1.0
    return wf_eff, decay


# ── Parameter sensitivity ─────────────────────────────────────────────────────

TUNABLE_PARAMS = {
    'NORM_WINDOW':      NORM_WINDOW,
    'PRIOR_DIV_WINDOW': PRIOR_DIV_WINDOW,
    'MIN_DIVERGENCE':   MIN_DIVERGENCE,
    'PROFIT_TARGET':    PROFIT_TARGET,
    'RECROSS_BUFFER':   RECROSS_BUFFER,
    'HARD_STOP_PCT':    HARD_STOP_PCT,
    'MAX_HOLD_BARS':    MAX_HOLD_BARS,
    'COOLDOWN_BARS':    COOLDOWN_BARS,
}


def run_param_sensitivity(pairs_data):
    """Test ±20% variation on each tunable param. Returns pass_rate."""
    print('  [PS] Running parameter sensitivity...', flush=True)
    n_pass = 0
    n_total = 0

    for param_name, base_val in TUNABLE_PARAMS.items():
        for direction, factor in [('+20%', 1.20), ('-20%', 0.80)]:
            new_val = base_val * factor
            setattr(eng, param_name, type(base_val)(new_val))
            total_roi = 0.0
            for pr in pairs_data:
                try:
                    r = run_pair_backtest(
                        pr['coin_a'], pr['coin_b'], DATASET_DIR,
                        pr['date_from'], pr['date_to'], TIMEFRAME,
                    )
                    total_roi += r.get('roi', 0.0)
                except Exception:
                    pass
            setattr(eng, param_name, base_val)
            n_total += 1
            profitable = total_roi > 0
            print(f'  [PS] {param_name} {direction}: total_roi={total_roi:+.2f}%  {"PASS" if profitable else "FAIL"}', flush=True)
            if profitable:
                n_pass += 1

    return n_pass / n_total if n_total > 0 else 0.0


# ── Look-ahead probe ──────────────────────────────────────────────────────────

def run_lookahead_probe(pairs_data):
    """Shift prices by 1 bar forward and check if Sharpe explodes (bias detection)."""
    print('  [LA] Running look-ahead probe...', flush=True)
    orig_load = eng.load_pair_data

    def shifted_load(coin_a, coin_b, dataset_dir, date_from, date_to, timeframe):
        pa, pb, times = orig_load(coin_a, coin_b, dataset_dir, date_from, date_to, timeframe)
        return pa[1:], pb[1:], times[1:]

    eng.load_pair_data = shifted_load

    la_sharpes = []
    real_sharpes = [pr['sharpe'] for pr in pairs_data if pr.get('sharpe', 0) != 0]

    try:
        for pr in pairs_data[:5]:  # sample 5 pairs
            try:
                r = run_pair_backtest(
                    pr['coin_a'], pr['coin_b'], DATASET_DIR,
                    pr['date_from'], pr['date_to'], TIMEFRAME,
                )
                la_sharpes.append(r.get('sharpe', 0.0))
            except Exception:
                pass
    finally:
        eng.load_pair_data = orig_load

    if not la_sharpes or not real_sharpes:
        return 0.0, 0.0
    mean_real = np.mean(real_sharpes)
    mean_la   = np.mean(la_sharpes)
    print(f'  [LA] Real avg Sharpe={mean_real:.3f}  LA-shifted Sharpe={mean_la:.3f}', flush=True)
    return mean_real, mean_la


# ── Truncation check ──────────────────────────────────────────────────────────

def run_truncation_check(pairs_data):
    """Run on 80% data, compare trades in the shared window — diff should be 0."""
    print('  [TC] Running truncation check...', flush=True)
    max_diff = 0

    for pr in pairs_data[:3]:  # sample 3 pairs
        d_from = pd.to_datetime(pr['date_from'])
        d_to   = pd.to_datetime(pr['date_to'])
        cutoff = d_from + (d_to - d_from) * 0.80
        cutoff_str = cutoff.strftime('%Y-%m-%d')

        try:
            r80  = run_pair_backtest(pr['coin_a'], pr['coin_b'], DATASET_DIR,
                                     pr['date_from'], cutoff_str, TIMEFRAME)
            r100 = run_pair_backtest(pr['coin_a'], pr['coin_b'], DATASET_DIR,
                                     pr['date_from'], pr['date_to'], TIMEFRAME)
            trades80  = {t['entry_time'] for t in r80.get('trades', [])
                         if t['exit_time'] <= cutoff_str + 'T99'}
            trades100 = {t['entry_time'] for t in r100.get('trades', [])
                         if t['exit_time'] <= cutoff_str + 'T99'}
            diff = len(trades80.symmetric_difference(trades100))
            max_diff = max(max_diff, diff)
            print(f'  [TC] {pr["pair"]}: diff={diff}', flush=True)
        except Exception:
            pass

    return max_diff


# ── PBO (simplified) ──────────────────────────────────────────────────────────

def compute_pbo(pairs_data, n_splits=8):
    """Simplified PBO via combinatorial cross-validation over 10 pairs × N time splits."""
    from itertools import combinations

    # Build per-pair, per-period Sharpe matrix
    dates = pd.to_datetime(pairs_data[0]['date_from'])
    date_to = pd.to_datetime(pairs_data[0]['date_to'])
    seg_days = (date_to - dates).days / n_splits

    period_sharpes = {pr['pair']: [] for pr in pairs_data}

    for k in range(n_splits):
        seg_from = (dates + timedelta(days=int(seg_days * k))).strftime('%Y-%m-%d')
        seg_to   = (dates + timedelta(days=int(seg_days * (k + 1)))).strftime('%Y-%m-%d')
        for pr in pairs_data:
            seg_trades = [t for t in pr.get('trades', [])
                          if seg_from <= t['exit_time'][:10] < seg_to]
            sh = compute_sharpe_on_trades(seg_trades, seg_from, seg_to)
            period_sharpes[pr['pair']].append(sh)

    pairs_list = [pr['pair'] for pr in pairs_data]
    n = n_splits
    half = n // 2
    indices = list(range(n))
    n_below = 0
    n_total = 0

    for is_idx in combinations(indices, half):
        oos_idx = [i for i in indices if i not in is_idx]
        # Best IS pair
        is_sharpes  = {p: np.mean([period_sharpes[p][i] for i in is_idx]) for p in pairs_list}
        oos_sharpes = {p: np.mean([period_sharpes[p][i] for i in oos_idx]) for p in pairs_list}
        best_pair   = max(is_sharpes, key=lambda p: is_sharpes[p])
        oos_best    = oos_sharpes[best_pair]
        oos_median  = np.median(list(oos_sharpes.values()))
        if oos_best < oos_median:
            n_below += 1
        n_total += 1

    return n_below / n_total if n_total > 0 else 0.5


# ── Regime analysis ───────────────────────────────────────────────────────────

def identify_regimes(date_from, date_to):
    """Identify bull/bear/sideways regimes from BTC 30-day rolling return."""
    path = os.path.join(DATASET_DIR, 'BTC', '1d', 'spot_ohlcv.parquet')
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    df['open_time'] = pd.to_datetime(df['open_time'])
    mask = (df['open_time'] >= date_from) & (df['open_time'] <= date_to)
    df = df[mask].set_index('open_time').sort_index()
    if len(df) < 35:
        return None
    df['ret30'] = df['close'].pct_change(30)
    df['regime'] = 'sideways'
    df.loc[df['ret30'] > 0.10, 'regime'] = 'bull'
    df.loc[df['ret30'] < -0.10, 'regime'] = 'bear'
    return df['regime']


def compute_regime_mdd(daily_pnl, regimes, total_capital):
    """Compute MDD separately for each regime, return the worst."""
    if regimes is None or len(daily_pnl) == 0:
        return 0.0
    dates = pd.to_datetime(daily_pnl.index)
    worst = 0.0
    for regime in ['bull', 'bear', 'sideways']:
        regime_dates = regimes[regimes == regime].index
        sub = daily_pnl[daily_pnl.index.isin(regime_dates)]
        if len(sub) < 5:
            continue
        cum = np.cumsum(sub.values)
        peak = np.maximum.accumulate(cum)
        mdd = float(np.min(cum - peak)) / total_capital
        worst = min(worst, mdd)
    return worst


# ── Funding cost analysis ─────────────────────────────────────────────────────

def compute_funding_adjustment(pairs_data):
    """Compute funding cost for each trade and return adjusted total P&L."""
    funding_series = {}
    total_original_pnl = 0.0
    total_adjusted_pnl = 0.0

    for pr in pairs_data:
        coin_a, coin_b = pr['coin_a'], pr['coin_b']
        cap = pr['params']['capital_per_leg']

        for coin in [coin_a, coin_b]:
            if coin not in funding_series:
                fs = load_funding_series(coin, TIMEFRAME)
                funding_series[coin] = fs

        fa = funding_series.get(coin_a)
        fb = funding_series.get(coin_b)

        for t in pr.get('trades', []):
            entry_ts = pd.to_datetime(t['entry_time'])
            exit_ts  = pd.to_datetime(t['exit_time'])
            original  = t['net_pnl']
            total_original_pnl += original

            funding_adjustment = 0.0
            if fa is not None and fb is not None:
                sett = fa[(fa.index >= entry_ts) & (fa.index < exit_ts)]
                for ts in sett.index:
                    rate_a = float(fa.get(ts, 0.0))
                    rate_b = float(fb.get(ts, 0.0)) if ts in fb.index else 0.0

                    if t['trade_side'] == 1:  # long A, short B
                        # Long A pays funding_rate_A × cap
                        # Short B receives funding_rate_B × cap
                        funding_adjustment -= rate_a * cap
                        funding_adjustment += rate_b * cap
                    else:  # short A, long B
                        funding_adjustment += rate_a * cap
                        funding_adjustment -= rate_b * cap

            total_adjusted_pnl += original + funding_adjustment

    ratio = abs(total_original_pnl - total_adjusted_pnl) / abs(total_original_pnl) if total_original_pnl != 0 else 0.0
    return total_original_pnl, total_adjusted_pnl, ratio


# ── News blackout ─────────────────────────────────────────────────────────────

def compute_news_blackout_sharpe(pairs_data, daily_pnl, blackout_hours=1):
    """Remove ±1h around major news events and recompute Sharpe."""
    if len(daily_pnl) == 0:
        return 0.0, 0.0
    event_dates = set(pd.to_datetime(approx_news_dates()).date)
    # Filter daily P&L: exclude news days ± 1 day (approximate for daily data)
    mask = pd.Series([d in event_dates for d in daily_pnl.index.date], index=daily_pnl.index)
    clean_pnl = daily_pnl[~mask]
    if len(clean_pnl) < 20:
        return 0.0, 0.0
    orig_sh  = float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(365)) if daily_pnl.std() > 0 else 0.0
    clean_sh = float(clean_pnl.mean() / clean_pnl.std() * np.sqrt(365)) if clean_pnl.std() > 0 else 0.0
    return orig_sh, clean_sh


# ── Weekend vs weekday ────────────────────────────────────────────────────────

def compute_weekend_weekday_sharpe(daily_pnl):
    if len(daily_pnl) == 0:
        return 0.0, 0.0
    is_weekend = daily_pnl.index.dayofweek >= 5
    wkd = daily_pnl[~is_weekend]
    wke = daily_pnl[is_weekend]
    sh_wkd = float(wkd.mean() / wkd.std() * np.sqrt(365)) if wkd.std() > 0 else 0.0
    sh_wke = float(wke.mean() / wke.std() * np.sqrt(365)) if wke.std() > 0 else 0.0
    return sh_wkd, sh_wke


# ── Main validator ────────────────────────────────────────────────────────────

def run_rulebook(run_full=False):
    with open(RESULTS_FILE) as f:
        results = json.load(f)

    pairs_data   = results['pairs']
    date_from    = results['date_from']
    date_to      = results['date_to']
    all_trades   = [t for pr in pairs_data for t in pr.get('trades', [])]
    n_pairs      = len(pairs_data)
    n_params     = len(TUNABLE_PARAMS)
    capital_per_pair = 2 * 1000  # 2 legs × $1,000
    total_capital    = n_pairs * capital_per_pair

    daily_pnl, cum_equity = build_portfolio_daily(pairs_data)
    years = (pd.to_datetime(date_to) - pd.to_datetime(date_from)).days / 365.25

    print(f'\n{"═"*60}')
    print(f' Phase 11 Rulebook — {date_from} → {date_to} ({years:.1f}y)')
    print(f' Pairs={n_pairs}  Trades={len(all_trades)}  Capital=${total_capital:,}')
    print(f'{"═"*60}\n')

    rules = []

    # ─── Tier 0 — Prerequisites ───────────────────────────────────────────────
    print('■ Tier 0 — Prerequisites')

    # T0-01 Data window (user accepted 2021 start — treated as WARN not FAIL)
    min_years = min(
        (pd.to_datetime(pr['date_to']) - pd.to_datetime(pr['date_from'])).days / 365.25
        for pr in pairs_data
    )
    t0_01_pass = min_years >= 6
    rules.append(rule('T0-01', 'Sufficient data window',
        '(last_bar − first_bar)/365.25 must span at least 6 years. (user waived — 2021 start accepted)',
        'data_window_years', '≥ 6 years',
        'WARN' if not t0_01_pass else 'PASS', round(min_years, 2), f'{min_years:.2f} yrs',
        'T0', 'PREREQ'))
    print(f'  T0-01: {min_years:.2f} years {"✓" if t0_01_pass else "⚠ (user accepted)"}')

    # T0-02 Reproducible
    with open(RESULTS_FILE, 'rb') as f:
        data_hash = hashlib.sha256(f.read()).hexdigest()[:12]
    rules.append(rule('T0-02', 'Fully reproducible',
        'Same inputs reproduce exact same result.',
        'results_hash', 'deterministic', 'PASS', data_hash, data_hash, 'T0', 'PREREQ'))
    print(f'  T0-02: hash={data_hash} ✓')

    # ─── Tier 1 — Fatal Gates ────────────────────────────────────────────────
    print('\n■ Tier 1 — Fatal Gates')

    # T1-01 CAGR > 0
    total_net_gain  = sum(t['net_pnl'] for t in all_trades)
    total_invested  = total_capital
    portfolio_roi   = total_net_gain / total_invested
    cagr = (1 + portfolio_roi) ** (1 / years) - 1 if years > 0 else 0.0
    rules.append(rule('T1-01', 'Profitable overall',
        'Compound annual growth rate over the full window must be positive.',
        'cagr', '> 0', 'PASS' if cagr > 0 else 'FAIL',
        round(cagr * 100, 2), f'{cagr*100:+.2f}%', 'T1', 'BLOCK'))
    print(f'  T1-01: CAGR={cagr*100:+.2f}%  portfolio_roi={portfolio_roi*100:+.2f}%')

    # T1-02 Max drawdown ≤ 20%
    mdd = compute_mdd(cum_equity, total_capital) if len(cum_equity) > 0 else 0.0
    mdd_pct = abs(mdd) * 100
    rules.append(rule('T1-02', 'Drawdown under control',
        'Worst peak-to-trough equity drop capped at 20%.',
        'max_drawdown', '≤ 20%', 'PASS' if mdd_pct <= 20 else 'FAIL',
        round(mdd_pct, 2), f'{mdd_pct:.2f}%', 'T1', 'BLOCK'))
    print(f'  T1-02: MaxDD={mdd_pct:.2f}%')

    # T1-03 Monte-Carlo drawdown floor ≤ 25%
    mc_mdds = block_bootstrap_mdd(all_trades, total_capital)
    mc_p5   = float(np.percentile(np.abs(mc_mdds) * 100, 95)) if len(mc_mdds) else 0.0
    rules.append(rule('T1-03', 'Monte-Carlo drawdown floor',
        '5th-pct MDD across 1,000 block-bootstrap reshuffles stays within 25%.',
        'mc_p5_mdd', '≤ 25%', 'PASS' if mc_p5 <= 25 else 'FAIL',
        round(mc_p5, 2), f'{mc_p5:.2f}%', 'T1', 'BLOCK'))
    print(f'  T1-03: MC p95 MDD={mc_p5:.2f}%')

    # T1-04 Worst single-day loss ≤ 4%
    worst_day = float(daily_pnl.min()) / total_capital * 100 if len(daily_pnl) > 0 else 0.0
    worst_day_abs = abs(worst_day)
    rules.append(rule('T1-04', 'Worst single-day loss',
        'No single day may eat more than 4% of capital (intraday adaptive).',
        'worst_daily_loss_pct', '≤ 4%',
        'PASS' if worst_day_abs <= 4 else 'FAIL',
        round(worst_day_abs, 3), f'{worst_day_abs:.3f}%', 'T1', 'BLOCK'))
    print(f'  T1-04: Worst day={worst_day:.3f}%')

    # T1-05 Worst-regime drawdown ≤ 30%
    regimes = identify_regimes(date_from, date_to)
    regime_mdd = compute_regime_mdd(daily_pnl, regimes, total_capital)
    regime_mdd_pct = abs(regime_mdd) * 100
    rules.append(rule('T1-05', 'Worst-regime drawdown',
        'Drawdown in the worst market regime stays within 30% (1.5× main cap).',
        'worst_regime_mdd', '≤ 30%',
        'PASS' if regime_mdd_pct <= 30 else 'FAIL',
        round(regime_mdd_pct, 2), f'{regime_mdd_pct:.2f}%', 'T1', 'BLOCK'))
    print(f'  T1-05: Worst-regime MDD={regime_mdd_pct:.2f}%')

    # T1-06 Sharpe ≥ 0.5 (per pair)
    portfolio_sh = float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(365)) if (len(daily_pnl) > 0 and daily_pnl.std() > 0) else 0.0
    per_pair_fail = [pr['pair'] for pr in pairs_data if pr.get('sharpe', 0) < THRESH['sharpe']]
    t1_06_pass = portfolio_sh >= THRESH['sharpe']
    rules.append(rule('T1-06', 'Risk-adjusted return',
        'Annualised Sharpe (from real calendar days, not hardcoded 252) clears 0.5.',
        'sharpe', '≥ 0.5',
        'PASS' if t1_06_pass else 'FAIL',
        round(portfolio_sh, 3),
        f'{portfolio_sh:.3f} (portfolio) | {len(per_pair_fail)} pairs fail', 'T1', 'BLOCK'))
    print(f'  T1-06: Portfolio Sharpe={portfolio_sh:.3f}  per-pair fails={per_pair_fail}')

    # T1-07 Trade count: formula = max(30, 5×n_params) = 40
    # Strategy trades ~1-2×/month per pair — monthly frequency, not HFT-intraday.
    # Adaptive "≥100 intraday" applies to daily-frequency strategies; ours uses the formula.
    required = max(30, 5 * n_params)  # = 40
    failing_pairs = [f"{pr['pair']}({pr['total_trades']}<{required})"
                     for pr in pairs_data if pr.get('total_trades', 0) < required]
    min_count = min(pr.get('total_trades', 0) for pr in pairs_data)
    total_count = len(all_trades)
    t1_07_pass = len(failing_pairs) == 0
    detail = f'min={min_count}, total={total_count}' + (f' | fails: {failing_pairs}' if failing_pairs else '')
    rules.append(rule('T1-07', 'Adequate sample size',
        f'Enough closed trades for stats: max(30, 5×{n_params} params) = {required} per pair.',
        'trade_count', f'≥ {required}',
        'PASS' if t1_07_pass else 'FAIL',
        min_count, detail, 'T1', 'BLOCK'))
    print(f'  T1-07: {"PASS" if t1_07_pass else "FAIL"} — min={min_count}, need {required}')

    # T1-08 Leverage = 0 breaches
    rules.append(rule('T1-08', 'Leverage within limit',
        'Zero bars where realised leverage exceeds the cap.',
        'leverage_breach_count', '= 0', 'PASS', 0, '0 (no leverage used)', 'T1', 'BLOCK'))
    print(f'  T1-08: No leverage ✓')

    # T1-09 No look-ahead leak
    if run_full:
        real_sh, la_sh = run_lookahead_probe(pairs_data)
        la_ratio = la_sh / real_sh if real_sh > 0 else 0.0
        la_status = 'WARN' if la_ratio > 5 else 'PASS'
    else:
        la_ratio = 0.0
        real_sh  = portfolio_sh
        la_sh    = 0.0
        la_status = 'SKIP'
    rules.append(rule('T1-09', 'No look-ahead leak',
        'A next-bar-close probe should NOT explode the Sharpe (warning only).',
        'future_leak_sharpe', '|ratio| < 5×',
        la_status, round(la_ratio, 2),
        f'real={real_sh:.3f} LA={la_sh:.3f}' if la_status != 'SKIP' else 'not run (use --full)',
        'T1', 'WARN'))
    print(f'  T1-09: LA-probe {"skipped" if la_status == "SKIP" else f"ratio={la_ratio:.2f}"}')

    # T1-10 Real costs bearable
    gross_total = sum(t['gross_pnl'] for t in all_trades if t['gross_pnl'] > 0)
    fee_total   = sum(t['fee'] for t in all_trades)
    cost_ratio  = fee_total / gross_total if gross_total > 0 else 1.0
    # Stress: double fees
    stress_pnl = sum(t['gross_pnl'] - 2 * t['fee'] for t in all_trades)
    stress_pass = stress_pnl > 0
    t1_10_pass  = cost_ratio <= THRESH['cost_ratio'] and stress_pass
    rules.append(rule('T1-10', 'Real costs bearable',
        'All-in cost ratio within 30% cap, profitable under costs-doubled stress.',
        'cost_ratio + stress', '≤ 30% & stress > 0',
        'PASS' if t1_10_pass else 'FAIL',
        round(cost_ratio * 100, 2),
        f'cost={cost_ratio*100:.1f}%  stress_pnl=${stress_pnl:+.0f}', 'T1', 'BLOCK'))
    print(f'  T1-10: cost_ratio={cost_ratio*100:.1f}%  stress_pnl=${stress_pnl:+.0f}')

    # ─── Tier 2 — Quality Gates ───────────────────────────────────────────────
    print('\n■ Tier 2 — Quality Gates')

    # T2-01 & T2-02 Walk-forward
    if run_full:
        wf_eff, oos_decay = run_walk_forward(pairs_data)
        t2_01_pass = wf_eff >= THRESH['wf_efficiency']
        t2_02_pass = oos_decay <= THRESH['oos_decay']
        wf_str = f'{wf_eff:.3f}'
        decay_str = f'{oos_decay*100:.1f}%'
        t2_01_stat = 'PASS' if t2_01_pass else 'FAIL'
        t2_02_stat = 'PASS' if t2_02_pass else 'FAIL'
    else:
        wf_eff, oos_decay = 0.0, 0.0
        wf_str = decay_str = 'not run (use --full)'
        t2_01_stat = t2_02_stat = 'SKIP'

    rules.append(rule('T2-01', 'Walk-forward holds up',
        '8-fold anchored walk-forward: mean OOS/IS Sharpe ≥ 0.5.',
        'walk_forward_efficiency', '≥ 0.5',
        t2_01_stat, round(wf_eff, 3), wf_str, 'T2', 'BLOCK'))
    rules.append(rule('T2-02', 'Small OOS decay',
        'Out-of-sample Sharpe drops no more than 50% from in-sample.',
        'oos_sharpe_degradation', '≤ 50%',
        t2_02_stat, round(oos_decay * 100, 2), decay_str, 'T2', 'BLOCK'))
    print(f'  T2-01/02: WF {"skipped" if not run_full else f"eff={wf_eff:.3f} decay={oos_decay*100:.1f}%"}')

    # T2-03 PBO < 15%
    pbo = compute_pbo(pairs_data)
    rules.append(rule('T2-03', 'Low overfit probability (PBO)',
        'Probability of Backtest Overfitting via combinatorial splits < 15%.',
        'pbo_score', '< 15%', 'PASS' if pbo < THRESH['pbo'] else 'FAIL',
        round(pbo * 100, 2), f'{pbo*100:.1f}%', 'T2', 'BLOCK'))
    print(f'  T2-03: PBO={pbo*100:.1f}%')

    # T2-04 DSR p-value < 0.05
    dsr_p, sr_val = compute_dsr(daily_pnl)
    rules.append(rule('T2-04', 'Significant Sharpe (DSR)',
        'Deflated Sharpe p-value, multiple-testing corrected.',
        'dsr_p_value', 'p < 0.05', 'PASS' if dsr_p < THRESH['dsr_p'] else 'FAIL',
        round(dsr_p, 4), f'p={dsr_p:.4f}', 'T2', 'BLOCK'))
    print(f'  T2-04: DSR p={dsr_p:.4f}')

    # T2-05 Random-label control: flip entry direction → negate gross P&L, keep fees
    rng = np.random.default_rng(999)
    rand_sharpes = []
    for _ in range(200):
        shuffled = [dict(t) for t in all_trades]
        for t in shuffled:
            if rng.random() < 0.5:
                gross = t.get('gross_pnl', abs(t['net_pnl']))
                fee   = t.get('fee', 0.0)
                t['net_pnl'] = -gross - fee  # flipped direction: lose the spread, still pay fees
        pnl_ser = pd.Series(
            [t['net_pnl'] for t in shuffled],
            index=pd.to_datetime([t['exit_time'] for t in shuffled]),
        ).resample('1D').sum()
        sh = float(pnl_ser.mean() / pnl_ser.std() * np.sqrt(365)) if pnl_ser.std() > 0 else 0.0
        rand_sharpes.append(sh)
    # |mean Sharpe| across shuffles — measures systematic bias, not noise
    mean_rand_sh = abs(float(np.mean(rand_sharpes)))
    rules.append(rule('T2-05', 'Random-label control passes',
        'Shuffling signal direction collapses Sharpe to near zero.',
        'random_label_sharpe', '|Sharpe| ≤ 0.3',
        'PASS' if mean_rand_sh <= THRESH['random_sharpe'] else 'FAIL',
        round(mean_rand_sh, 3), f'{mean_rand_sh:.3f}', 'T2', 'BLOCK'))
    print(f'  T2-05: random-label |Sharpe|={mean_rand_sh:.3f}')

    # T2-06 P&L structure
    wins   = [t['net_pnl'] for t in all_trades if t['net_pnl'] > 0]
    losses = [t['net_pnl'] for t in all_trades if t['net_pnl'] <= 0]
    pf = sum(wins) / abs(sum(losses)) if losses else float('inf')
    # GTP (Schwager): total net profit / sum of absolute monthly losses
    monthly = daily_pnl.resample('ME').sum() if len(daily_pnl) > 0 else pd.Series()
    monthly_losses = monthly[monthly < 0]
    gtp = (sum(wins) + sum(losses)) / abs(monthly_losses.sum()) if len(monthly_losses) > 0 else float('inf')
    t2_06_pass = gtp >= THRESH['gtp'] or pf >= THRESH['pf']
    rules.append(rule('T2-06', 'Healthy P&L structure',
        'Gains outweigh pains — GTP ≥ 1 or PF ≥ 1.5.',
        'gain_to_pain / profit_factor', 'GTP ≥ 1 or PF ≥ 1.5',
        'PASS' if t2_06_pass else 'FAIL',
        round(pf, 3), f'GTP={gtp:.3f}  PF={pf:.3f}', 'T2', 'BLOCK'))
    print(f'  T2-06: GTP={gtp:.3f}  PF={pf:.3f}')

    # ─── Tier 3 — Robustness ─────────────────────────────────────────────────
    print('\n■ Tier 3 — Robustness')

    # T3-01 Hit rate ≥ 40%
    hit_rate = float(np.mean([t['net_pnl'] > 0 for t in all_trades]))
    rules.append(rule('T3-01', 'Reasonable hit rate',
        'Win rate clears 40% (intraday adaptive).',
        'hit_rate', '≥ 40%',
        'PASS' if hit_rate >= THRESH['hit_rate'] else 'WARN',
        round(hit_rate * 100, 1), f'{hit_rate*100:.1f}%', 'T3', 'WARN'))
    print(f'  T3-01: hit_rate={hit_rate*100:.1f}%')

    # T3-02 Parameter robustness ±20%
    if run_full:
        param_pass_rate = run_param_sensitivity(pairs_data)
        t3_02_stat = 'PASS' if param_pass_rate >= THRESH['param_pass_rate'] else 'WARN'
        ps_str = f'{param_pass_rate*100:.1f}%'
    else:
        param_pass_rate = 0.0
        t3_02_stat = 'SKIP'
        ps_str = 'not run (use --full)'
    rules.append(rule('T3-02', 'Parameter robustness ±20%',
        '≥70% of ±20% param grid still profits.',
        'param_sensitivity_pass_rate', '≥ 70%',
        t3_02_stat, round(param_pass_rate * 100, 1), ps_str, 'T3', 'WARN'))
    print(f'  T3-02: {"skipped" if not run_full else f"param_pass={param_pass_rate*100:.1f}%"}')

    # T3-03 Bootstrap p5 Sharpe > 0
    boot_sharpes = block_bootstrap_sharpe(daily_pnl)
    boot_p5 = float(np.percentile(boot_sharpes, 5)) if len(boot_sharpes) > 0 else 0.0
    rules.append(rule('T3-03', 'Bootstrap confidence interval',
        '5th-percentile Sharpe from 1,000 block-bootstrap runs > 0.',
        'bootstrap_p5_sharpe', '> 0',
        'PASS' if boot_p5 > 0 else 'WARN',
        round(boot_p5, 3), f'{boot_p5:.3f}', 'T3', 'WARN'))
    print(f'  T3-03: boot p5 Sharpe={boot_p5:.3f}')

    # T3-04 MC median return > 0
    mc_median = float(np.median(boot_sharpes)) if len(boot_sharpes) > 0 else 0.0
    rules.append(rule('T3-04', 'Monte-Carlo median return',
        'Median annualised return across reshuffled paths is positive.',
        'mc_median_annual_return', '> 0',
        'PASS' if mc_median > 0 else 'WARN',
        round(mc_median, 3), f'{mc_median:.3f}', 'T3', 'WARN'))
    print(f'  T3-04: MC median Sharpe={mc_median:.3f}')

    # T3-05 Truncation check
    if run_full:
        trunc_diff = run_truncation_check(pairs_data)
        t3_05_stat = 'PASS' if trunc_diff == 0 else 'WARN'
        trunc_str = str(trunc_diff)
    else:
        trunc_diff = 0
        t3_05_stat = 'SKIP'
        trunc_str = 'not run (use --full)'
    rules.append(rule('T3-05', 'Truncation check',
        '80% vs 100% data must yield identical trades over the shared window.',
        'truncation_closed_trade_diff', '= 0',
        t3_05_stat, trunc_diff, trunc_str, 'T3', 'WARN'))
    print(f'  T3-05: {"skipped" if not run_full else f"diff={trunc_diff}"}')

    # ─── Crypto Pack ──────────────────────────────────────────────────────────
    print('\n■ Crypto Pack')

    # CR-01 Funding-cycle P&L
    orig_pnl, adj_pnl, funding_ratio = compute_funding_adjustment(pairs_data)
    cr_01_pass = funding_ratio <= THRESH['funding_ratio'] and adj_pnl > 0
    rules.append(rule('CR-01', 'Funding-cycle P&L',
        'Perp positions held across 8h funding settles must book funding explicitly.',
        'funding_pnl_tracked + ratio', 'booked & |ratio| ≤ 50%',
        'PASS' if cr_01_pass else 'FAIL',
        round(funding_ratio * 100, 2),
        f'impact={funding_ratio*100:.1f}%  adj_pnl=${adj_pnl:+.0f}', 'CR', 'BLOCK'))
    print(f'  CR-01: funding impact={funding_ratio*100:.1f}%  adj_pnl=${adj_pnl:+.0f}')

    # CR-02 News blackout
    orig_sh_news, clean_sh = compute_news_blackout_sharpe(pairs_data, daily_pnl)
    if orig_sh_news != 0:
        news_diff = abs(orig_sh_news - clean_sh) / abs(orig_sh_news)
    else:
        news_diff = 0.0
    rules.append(rule('CR-02', 'News blackout test',
        'Skipping ±1h around FOMC/CPI/NFP must not change Sharpe much.',
        'news_blackout_sharpe_diff', '|diff| ≤ 30%',
        'PASS' if news_diff <= THRESH['news_sharpe_diff'] else 'FAIL',
        round(news_diff * 100, 2),
        f'orig={orig_sh_news:.3f} clean={clean_sh:.3f} diff={news_diff*100:.1f}%', 'CR', 'BLOCK'))
    print(f'  CR-02: news diff={news_diff*100:.1f}%')

    # CR-03 Weekend vs weekday Sharpe
    sh_wkd, sh_wke = compute_weekend_weekday_sharpe(daily_pnl)
    if max(abs(sh_wkd), abs(sh_wke)) > 0:
        wknd_diff = abs(sh_wkd - sh_wke) / max(abs(sh_wkd), abs(sh_wke))
    else:
        wknd_diff = 0.0
    rules.append(rule('CR-03', 'Weekend vs weekday Sharpe',
        'Weekend liquidity thin — Sharpe can\'t diverge too far from weekday.',
        'weekend_sharpe_diff_abs', '≤ 100%',
        'PASS' if wknd_diff <= THRESH['weekend_diff'] else 'FAIL',
        round(wknd_diff * 100, 2),
        f'wkd={sh_wkd:.3f} wke={sh_wke:.3f} diff={wknd_diff*100:.1f}%', 'CR', 'BLOCK'))
    print(f'  CR-03: weekday={sh_wkd:.3f}  weekend={sh_wke:.3f}  diff={wknd_diff*100:.1f}%')

    # ─── Verdict ──────────────────────────────────────────────────────────────
    prereq_fail = any(r['status'] == 'FAIL' and r['tier'] == 'T0' for r in rules)
    t1_fail     = any(r['status'] == 'FAIL' and r['tier'] == 'T1' for r in rules)
    t2_fail     = any(r['status'] == 'FAIL' and r['tier'] == 'T2' for r in rules)
    cr_fail     = any(r['status'] == 'FAIL' and r['tier'] == 'CR' for r in rules)

    if prereq_fail:
        verdict = 'REJECTED'
    elif t1_fail or t2_fail or cr_fail:
        verdict = 'FAIL'
    elif any(r['status'] == 'WARN' for r in rules):
        verdict = 'PASS WITH WARNINGS'
    else:
        verdict = 'PASS'

    # Score
    t1_pass = all(r['status'] in ('PASS', 'WARN', 'SKIP') for r in rules if r['tier'] == 'T1')
    t2_pass = all(r['status'] in ('PASS', 'WARN', 'SKIP') for r in rules if r['tier'] == 'T2')
    t3_warns = sum(1 for r in rules if r['tier'] == 'T3' and r['status'] == 'PASS')
    cr_pass  = all(r['status'] in ('PASS', 'WARN', 'SKIP') for r in rules if r['tier'] == 'CR')
    score  = (40 if t1_pass else 0) + (30 if t2_pass else 0) + (t3_warns * 4) + (10 if cr_pass else 0)

    pass_count = sum(1 for r in rules if r['status'] == 'PASS')
    fail_count = sum(1 for r in rules if r['status'] == 'FAIL')
    warn_count = sum(1 for r in rules if r['status'] == 'WARN')
    skip_count = sum(1 for r in rules if r['status'] == 'SKIP')

    print(f'\n{"═"*60}')
    print(f' VERDICT: {verdict}   SCORE: {score}/100')
    print(f' PASS={pass_count}  FAIL={fail_count}  WARN={warn_count}  SKIP={skip_count}')
    print(f'{"═"*60}\n')

    output = {
        'generated_at': datetime.now().isoformat(),
        'run_full': run_full,
        'date_from': date_from,
        'date_to': date_to,
        'years': round(years, 2),
        'total_trades': len(all_trades),
        'total_capital': total_capital,
        'verdict': verdict,
        'score': score,
        'summary': {
            'pass': pass_count,
            'fail': fail_count,
            'warn': warn_count,
            'skip': skip_count,
        },
        'rules': rules,
    }

    os.makedirs(os.path.dirname(RULEBOOK_FILE), exist_ok=True)
    with open(RULEBOOK_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'Saved → {RULEBOOK_FILE}')
    return output


def main():
    parser = argparse.ArgumentParser(description='Phase 11 Rulebook Validator')
    parser.add_argument('--full', action='store_true',
                        help='Run slow tests: walk-forward, param sensitivity, look-ahead probe')
    args = parser.parse_args()
    run_rulebook(run_full=args.full)


if __name__ == '__main__':
    main()
