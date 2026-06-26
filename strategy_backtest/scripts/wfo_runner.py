"""
strategy_backtest/scripts/wfo_runner.py — Anchored expanding-window walk-forward.

Splits the strategy's date window into (n_folds + 1) equal segments.
Fold k: IS = first k segments, OOS = next 1 segment.
Reports WF efficiency, OOS/IS MDD ratio, and fold-level Sharpe.

Usage:
    python strategy_backtest/scripts/wfo_runner.py --strategy 3
    python strategy_backtest/scripts/wfo_runner.py --strategy 3 --folds 8
    python strategy_backtest/scripts/wfo_runner.py --strategy 3 --save wfo_3.json
"""

import os
import sys
import json
import argparse

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from strategy_backtest.settings import STRATEGY_LIBRARY
from strategy_backtest.run_backtest import run_strategy

THRESH = {
    'wf_efficiency':    0.50,
    'oos_is_mdd_ratio': 1.50,
    'oos_sharpe_decay': 0.50,
}


def _fmt(v):
    if v is None:
        return 'N/A'
    return f"{v:+.3f}"


def run_wfo(strategy_id: str, n_folds: int = 8, save_path: str = None) -> dict:
    if strategy_id not in STRATEGY_LIBRARY:
        print(f"[ERROR] Strategy '{strategy_id}' not found in STRATEGY_LIBRARY.")
        return {}

    cfg      = STRATEGY_LIBRARY[strategy_id]
    data_cfg = cfg['data']
    date_from = pd.Timestamp(data_cfg['date_from'])
    date_to   = pd.Timestamp(data_cfg['date_to'])
    total_days = (date_to - date_from).days

    if total_days < 365 * 2:
        print(f"[WARN] Window too short for {n_folds}-fold WFO ({total_days} days). Need ≥ 2 years.")
        return {}

    seg_days = total_days / (n_folds + 1)

    print(f"\n{'='*72}")
    print(f"  Walk-Forward: strategy {strategy_id} | {cfg['id']}")
    print(f"  Period : {date_from.date()} → {date_to.date()}  ({total_days} days)")
    print(f"  Folds  : {n_folds}  |  Segment ≈ {int(seg_days)} days each")
    print(f"{'='*72}")

    folds = []
    for k in range(1, n_folds + 1):
        is_start  = date_from
        is_end    = date_from + pd.Timedelta(days=seg_days * k)
        oos_start = is_end
        oos_end   = date_from + pd.Timedelta(days=seg_days * (k + 1))
        if oos_end > date_to:
            oos_end = date_to
        if oos_end <= oos_start:
            break

        print(f"\n  Fold {k}/{n_folds}")
        print(f"    IS  : {is_start.date()} → {is_end.date()}")
        print(f"    OOS : {oos_start.date()} → {oos_end.date()}")

        try:
            is_res  = run_strategy(cfg,
                                   date_from=is_start.strftime('%Y-%m-%d'),
                                   date_to=is_end.strftime('%Y-%m-%d'))
            oos_res = run_strategy(cfg,
                                   date_from=oos_start.strftime('%Y-%m-%d'),
                                   date_to=oos_end.strftime('%Y-%m-%d'))
        except Exception as e:
            print(f"    [ERROR] {e}")
            continue

        is_sharpe  = float(is_res.get('Sharpe Ratio', 0.0))
        oos_sharpe = float(oos_res.get('Sharpe Ratio', 0.0))
        is_mdd     = abs(float(is_res.get('Max Drawdown %', 0.0)))
        oos_mdd    = abs(float(oos_res.get('Max Drawdown %', 0.0)))
        is_trades  = int(is_res.get('Total Trades', 0))
        oos_trades = int(oos_res.get('Total Trades', 0))

        efficiency  = oos_sharpe / is_sharpe if is_sharpe > 0 else 0.0
        mdd_ratio   = oos_mdd / is_mdd if is_mdd > 0 else 0.0

        fold_res = {
            'fold':        k,
            'is_start':    str(is_start.date()),
            'is_end':      str(is_end.date()),
            'oos_start':   str(oos_start.date()),
            'oos_end':     str(oos_end.date()),
            'is_sharpe':   round(is_sharpe,  3),
            'oos_sharpe':  round(oos_sharpe, 3),
            'is_mdd':      round(is_mdd,  2),
            'oos_mdd':     round(oos_mdd, 2),
            'is_trades':   is_trades,
            'oos_trades':  oos_trades,
            'efficiency':  round(efficiency, 3) if efficiency != float('inf') else None,
            'mdd_ratio':   round(mdd_ratio,  3) if mdd_ratio  != float('inf') else None,
        }
        folds.append(fold_res)

        eff_str = _fmt(efficiency) if efficiency != float('inf') else 'INF'
        mdd_str = _fmt(mdd_ratio)  if mdd_ratio  != float('inf') else 'INF'
        print(f"    IS  Sharpe={is_sharpe:+.3f}  MDD={is_mdd:.1f}%  Trades={is_trades}")
        print(f"    OOS Sharpe={oos_sharpe:+.3f}  MDD={oos_mdd:.1f}%  Trades={oos_trades}")
        print(f"    → Efficiency={eff_str}  MDD_ratio={mdd_str}")

    if not folds:
        print("[ERROR] No folds completed.")
        return {}

    valid_eff  = [f['efficiency']  for f in folds if f['efficiency']  is not None]
    valid_mdd  = [f['mdd_ratio']   for f in folds if f['mdd_ratio']   is not None]
    mean_eff   = float(np.mean(valid_eff))  if valid_eff else 0.0
    mean_mdd   = float(np.mean(valid_mdd))  if valid_mdd else 0.0
    pos_oos    = sum(1 for f in folds if f['oos_sharpe'] > 0)
    is_sharpes = [f['is_sharpe']  for f in folds]
    oos_sharpes= [f['oos_sharpe'] for f in folds]
    # OOS/IS decay: mean(IS) - mean(OOS)
    decay = float(np.mean(is_sharpes) - np.mean(oos_sharpes)) if is_sharpes else 0.0

    wf_pass   = mean_eff >= THRESH['wf_efficiency']
    mdd_pass  = mean_mdd <= THRESH['oos_is_mdd_ratio']
    dec_pass  = decay    <= THRESH['oos_sharpe_decay']

    print(f"\n{'='*72}")
    print(f"  SUMMARY")
    print(f"  WF Efficiency    : {mean_eff:+.3f}  (≥ {THRESH['wf_efficiency']})  → {'PASS ✓' if wf_pass  else 'FAIL ✗'}")
    print(f"  OOS/IS MDD Ratio : {mean_mdd:+.3f}  (≤ {THRESH['oos_is_mdd_ratio']}) → {'PASS ✓' if mdd_pass else 'FAIL ✗'}")
    print(f"  IS→OOS Decay     : {decay:+.3f}  (≤ {THRESH['oos_sharpe_decay']})  → {'PASS ✓' if dec_pass else 'FAIL ✗'}")
    print(f"  Positive OOS     : {pos_oos}/{len(folds)} folds")
    print(f"{'='*72}")

    result = {
        'strategy_id':      strategy_id,
        'strategy_name':    cfg['id'],
        'n_folds':          len(folds),
        'wf_efficiency':    round(mean_eff,  3),
        'oos_is_mdd_ratio': round(mean_mdd,  3),
        'oos_is_decay':     round(decay,     3),
        'positive_oos':     pos_oos,
        'total_folds':      len(folds),
        'wf_pass':          wf_pass,
        'mdd_ratio_pass':   mdd_pass,
        'decay_pass':       dec_pass,
        'folds':            folds,
    }

    if save_path:
        out = os.path.join(_ROOT, save_path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w') as fh:
            json.dump(result, fh, indent=2)
        print(f"\n  Saved → {out}")

    return result


def main():
    parser = argparse.ArgumentParser(description='Walk-Forward Optimizer for strategy_backtest strategies')
    parser.add_argument('--strategy', required=True, help='Strategy ID (e.g. 3, 87, 108)')
    parser.add_argument('--folds',    type=int, default=8, help='Number of WF folds (default 8)')
    parser.add_argument('--save',     default=None, help='Save results to JSON path')
    args = parser.parse_args()
    run_wfo(args.strategy, args.folds, args.save)


if __name__ == '__main__':
    main()
