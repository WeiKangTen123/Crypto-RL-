"""
Phase 10 — Pure Formula Parameter Optimizer
Grid search over MIN_ENTRY_Z, MAX_HOLD, Z_STOP_LOSS, OLS_WINDOW, ZSCORE_WINDOW.
Ranks by total ROI and Sharpe across all cointegrated pairs.

Usage:
  python phase_10/optimize.py
  python phase_10/optimize.py --tf 1h
  python phase_10/optimize.py --tf 5m --date_from 2024-01-01 --date_to 2025-01-01
"""

import os, sys, json, itertools, argparse
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import phase_10.engine as eng
from phase_10.engine import PAIRS, TIMEFRAME_MINUTES

DATASET_DIR  = os.path.join(_ROOT, 'dataset')
RESULTS_FILE = os.path.join(_ROOT, 'phase_10', 'data', 'optimize_results.json')

# ── Parameter grid ────────────────────────────────────────────────────────────
# OLS_WINDOW / ZSCORE_WINDOW in 1h-equivalent hours (engine scales internally)
GRID = {
    'OLS_WINDOW':     [36, 72],          # hedge ratio lookback (hours)
    'ZSCORE_WINDOW':  [18, 36],          # z-score rolling window (hours)
    'MIN_ENTRY_Z':    [1.5, 1.8, 2.0],  # entry threshold
    'MAX_HOLD_H':     [8, 24, 72, None], # max hold in hours (None = half-life)
    'Z_STOP_LOSS':    [2.5, 3.0],        # hard stop z-score
}


def patch(ols, zscore, min_z, zstop):
    """Monkey-patch engine module constants for this run."""
    eng.OLS_WINDOW      = ols
    eng.ZSCORE_WINDOW   = zscore
    eng.MIN_ENTRY_Z     = min_z
    eng.Z_STOP_LOSS     = zstop
    eng.MAX_ENTRY_Z     = zstop - 0.10
    # BB window kept but irrelevant (pure formula — bands not used for trading)
    eng.BB_WINDOW       = 20


def run_combo(combo, tf, date_from, date_to):
    ols, zscore, min_z, hold_h, zstop = combo
    patch(ols, zscore, min_z, zstop)

    # Convert max hold hours → bars for this timeframe
    bars_per_hour = 60 // TIMEFRAME_MINUTES[tf]
    max_hold_bars = int(hold_h * bars_per_hour) if hold_h is not None else None

    pair_results = []
    for coin_a, coin_b in PAIRS:
        try:
            r = eng.run_pair_backtest(
                coin_a, coin_b, DATASET_DIR,
                date_from=date_from, date_to=date_to,
                timeframe=tf,
                max_hold_override=max_hold_bars,
            )
            if r.get('error'):
                continue
            pair_results.append(r)
        except Exception as e:
            pass

    if not pair_results:
        return None

    coint_pairs = [r for r in pair_results if r.get('cointegrated')]
    if not coint_pairs:
        return None

    total_roi    = sum(r['roi']    for r in coint_pairs)
    avg_sharpe   = sum(r['sharpe'] for r in coint_pairs) / len(coint_pairs)
    total_trades = sum(r['total_trades'] for r in coint_pairs)
    avg_wr       = sum(r['win_rate'] for r in coint_pairs) / len(coint_pairs)
    avg_dd       = sum(r['max_drawdown'] for r in coint_pairs) / len(coint_pairs)
    n_coint      = len(coint_pairs)

    return {
        'ols_window':    ols,
        'zscore_window': zscore,
        'min_entry_z':   min_z,
        'max_hold_h':    hold_h,
        'z_stop_loss':   zstop,
        'n_coint_pairs': n_coint,
        'total_roi':     round(total_roi, 2),
        'avg_sharpe':    round(avg_sharpe, 3),
        'total_trades':  total_trades,
        'avg_win_rate':  round(avg_wr, 1),
        'avg_drawdown':  round(avg_dd, 2),
        'pair_detail':   [
            {'pair': r['pair'], 'roi': r['roi'], 'sharpe': r['sharpe'],
             'trades': r['total_trades'], 'win_rate': r['win_rate']}
            for r in coint_pairs
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tf',        default='1h', choices=sorted(TIMEFRAME_MINUTES.keys()))
    parser.add_argument('--date_from', default='2023-01-01')
    parser.add_argument('--date_to',   default='2026-05-31')
    args = parser.parse_args()

    combos = list(itertools.product(
        GRID['OLS_WINDOW'],
        GRID['ZSCORE_WINDOW'],
        GRID['MIN_ENTRY_Z'],
        GRID['MAX_HOLD_H'],
        GRID['Z_STOP_LOSS'],
    ))
    total = len(combos)
    print(f'Phase 10 Pure Formula Optimizer')
    print(f'TF: {args.tf} | Period: {args.date_from} → {args.date_to}')
    print(f'Grid: {total} combinations × {len(PAIRS)} pairs = {total * len(PAIRS)} runs')
    print('-' * 70)

    all_results = []
    for idx, combo in enumerate(combos, 1):
        ols, zscore, min_z, hold_h, zstop = combo
        label = f'OLS={ols}h Z={zscore}h entry={min_z} hold={hold_h or "HL"}h stop={zstop}'
        print(f'[{idx:>3}/{total}] {label}', end=' ... ', flush=True)

        result = run_combo(combo, args.tf, args.date_from, args.date_to)
        if result is None:
            print('no coint pairs')
            continue

        all_results.append(result)
        print(f'ROI={result["total_roi"]:+.1f}%  Sharpe={result["avg_sharpe"]:+.3f}  Trades={result["total_trades"]}')

    if not all_results:
        print('No results.')
        return

    # ── Rank results ─────────────────────────────────────────────────────────
    by_roi    = sorted(all_results, key=lambda x: x['total_roi'],  reverse=True)
    by_sharpe = sorted(all_results, key=lambda x: x['avg_sharpe'], reverse=True)

    print('\n' + '=' * 70)
    print('TOP 10 BY TOTAL ROI')
    print('=' * 70)
    print(f'{"OLS":>5} {"ZSCO":>5} {"MINZ":>5} {"HOLD":>6} {"STOP":>5} | {"ROI%":>7} {"SHRP":>7} {"TRDS":>6} {"WR%":>6}')
    for r in by_roi[:10]:
        h = f'{r["max_hold_h"]}h' if r['max_hold_h'] else 'HL'
        print(f'{r["ols_window"]:>5} {r["zscore_window"]:>5} {r["min_entry_z"]:>5} {h:>6} {r["z_stop_loss"]:>5} | '
              f'{r["total_roi"]:>+7.1f} {r["avg_sharpe"]:>+7.3f} {r["total_trades"]:>6} {r["avg_win_rate"]:>6.1f}')

    print('\n' + '=' * 70)
    print('TOP 10 BY AVG SHARPE')
    print('=' * 70)
    print(f'{"OLS":>5} {"ZSCO":>5} {"MINZ":>5} {"HOLD":>6} {"STOP":>5} | {"ROI%":>7} {"SHRP":>7} {"TRDS":>6} {"WR%":>6}')
    for r in by_sharpe[:10]:
        h = f'{r["max_hold_h"]}h' if r['max_hold_h'] else 'HL'
        print(f'{r["ols_window"]:>5} {r["zscore_window"]:>5} {r["min_entry_z"]:>5} {h:>6} {r["z_stop_loss"]:>5} | '
              f'{r["total_roi"]:>+7.1f} {r["avg_sharpe"]:>+7.3f} {r["total_trades"]:>6} {r["avg_win_rate"]:>6.1f}')

    output = {
        'generated_at': datetime.now().isoformat(),
        'tf': args.tf,
        'date_from': args.date_from,
        'date_to': args.date_to,
        'top_roi':    by_roi[:20],
        'top_sharpe': by_sharpe[:20],
        'all':        all_results,
    }
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'\nSaved → {RESULTS_FILE}')

    best = by_roi[0]
    h = f'{best["max_hold_h"]}h' if best['max_hold_h'] else 'half-life'
    print(f'\nBEST CONFIG (ROI): OLS={best["ols_window"]}h  ZSCORE={best["zscore_window"]}h  '
          f'ENTRY_Z={best["min_entry_z"]}  MAX_HOLD={h}  STOP={best["z_stop_loss"]}')
    print(f'→ Total ROI: {best["total_roi"]:+.2f}%  |  Avg Sharpe: {best["avg_sharpe"]:+.3f}  '
          f'|  Trades: {best["total_trades"]}  |  Win Rate: {best["avg_win_rate"]:.1f}%')


if __name__ == '__main__':
    main()
