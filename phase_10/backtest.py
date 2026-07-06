"""
Phase 10 — Pairs Trading Backtest Runner
Runs all 36 pair combinations across configurable timeframes and saves results.

Output filename: results_{mode}_{timeframe}.json
  e.g. results_advanced_1h.json, results_wright_4h.json

Usage:
  python phase_10/backtest.py
  python phase_10/backtest.py --pair BTC-ETH
  python phase_10/backtest.py --mode wright --timeframe 4h
  python phase_10/backtest.py --signal_timeframe 1h --timeframe 15m
"""

import os
import sys
import json
import argparse
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import importlib

DATASET_DIR = os.path.join(_ROOT, 'dataset')


def run_all(pairs, date_from, date_to, timeframe, signal_timeframe):
    global results_file
    results  = []
    total    = len(pairs)

    for idx, (coin_a, coin_b) in enumerate(pairs, 1):
        label = f'{coin_a}-{coin_b}'
        print(f'[{idx}/{total}] Running {label}...', flush=True)
        try:
            r = engine.run_pair_backtest(
                coin_a, coin_b, DATASET_DIR, date_from, date_to,
                timeframe=timeframe, signal_timeframe=signal_timeframe,
            )
            tag = 'COINT' if r.get('cointegrated') else 'NOCOINT'
            sharpe = r.get('sharpe', 0)
            roi    = r.get('roi', 0)
            trades = r.get('total_trades', 0)
            print(f'  [{tag}] ADF={r.get("adf_pvalue","?")}  Sharpe={sharpe}  ROI={roi}%  Trades={trades}', flush=True)
        except Exception as e:
            print(f'  [ERROR] {e}', flush=True)
            r = {'pair': label, 'coin_a': coin_a, 'coin_b': coin_b, 'error': str(e), 'cointegrated': False}
        results.append(r)

    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    output = {
        'generated_at': datetime.now().isoformat(),
        'date_from':    date_from,
        'date_to':      date_to,
        'timeframe':    timeframe,
        'signal_timeframe': signal_timeframe or timeframe,
        'execution_timeframe': timeframe,
        'pairs':        results,
    }
    with open(results_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'\nSaved → {results_file}')
    return output


def main():
    parser = argparse.ArgumentParser(description='Phase 10 Pairs Trading Backtest')
    parser.add_argument('--pair',      default=None,  help='Single pair e.g. BTC-ETH (default: all pairs)')
    parser.add_argument('--date_from', default='2023-01-01', help='Start date YYYY-MM-DD')
    parser.add_argument('--date_to',   default='2026-05-31', help='End date YYYY-MM-DD')
    parser.add_argument('--timeframe', default='1h',  help='Execution timeframe, e.g. 1h, 15m, 5m, 4h, 1d')
    parser.add_argument('--signal_timeframe', default=None,
                        help='Signal/model timeframe for MTF mode (e.g. 1h with 15m execution).')
    parser.add_argument('--mode', default='advanced', choices=['advanced', 'wright'],
                        help='Which engine to run: advanced (OLS/Z-score) or wright')
    args = parser.parse_args()

    if args.mode == 'wright':
        engine = importlib.import_module('phase_10.wright_engine')
    else:
        engine = importlib.import_module('phase_10.engine')

    # Coarser-than-1h TFs must run as signal_tf with 1h execution.
    COARSE_TFS = {'4h', '1d', '2d'}
    execution_tf = args.timeframe
    signal_tf    = args.signal_timeframe
    if args.timeframe in COARSE_TFS and not args.signal_timeframe:
        signal_tf    = args.timeframe
        execution_tf = '1h'

    # Output file label: for fine-grained execution TFs, use execution_tf (e.g. 15m run → _15m).
    # For coarser signal-only TFs with 1h execution, use signal_tf (e.g. 4h signal → _4h).
    if signal_tf and signal_tf != execution_tf:
        # Coarse signal / fine execution (MTF): label by signal_tf
        tf_label = signal_tf if signal_tf in COARSE_TFS else execution_tf
    else:
        tf_label = execution_tf

    # Auto-name output file: results_{mode}_{tf_label}.json
    results_file = os.path.join(
        _ROOT, 'phase_10', 'data',
        f'results_{args.mode}_{tf_label}.json'
    )

    run_all.__globals__['engine'] = engine
    run_all.__globals__['results_file'] = results_file

    if args.pair:
        parts = args.pair.split('-')
        if len(parts) != 2:
            print('ERROR: --pair must be in format COIN_A-COIN_B e.g. BTC-ETH')
            sys.exit(1)
        pairs = [(parts[0].upper(), parts[1].upper())]
    else:
        pairs = engine.PAIRS

    print(f'Phase 10 Pairs Trading Backtest ({args.mode.upper()} MODE)')
    print(f'Period : {args.date_from} → {args.date_to}')
    print(f'TF     : signal={signal_tf or execution_tf} execution={execution_tf}')
    print(f'Pairs  : {len(pairs)} pairs')
    print(f'Output : {results_file}')
    print('-' * 50)
    run_all(pairs, args.date_from, args.date_to, execution_tf, signal_tf)


if __name__ == '__main__':
    main()
