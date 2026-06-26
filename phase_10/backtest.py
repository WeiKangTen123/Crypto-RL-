"""
Phase 10 — Pairs Trading Backtest Runner
Runs all 10 pair combinations for BTC/ETH/BNB/SOL/XRP and saves results.json.

Usage:
  python phase_10/backtest.py
  python phase_10/backtest.py --pair BTC-ETH
  python phase_10/backtest.py --date_from 2023-01-01 --date_to 2026-05-31
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
# We will import the engine dynamically based on mode

DATASET_DIR  = os.path.join(_ROOT, 'dataset')
RESULTS_FILE = os.path.join(_ROOT, 'phase_10', 'data', 'results.json')
RESULTS_WRIGHT_FILE = os.path.join(_ROOT, 'phase_10', 'data', 'results_wright.json')


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
    parser.add_argument('--pair',      default=None,     help='Single pair e.g. BTC-ETH (default: all 10)')
    parser.add_argument('--date_from', default='2023-01-01', help='Start date YYYY-MM-DD')
    parser.add_argument('--date_to',   default='2026-05-31',   help='End date YYYY-MM-DD')
    parser.add_argument('--timeframe', default='1h',
                        help='Execution timeframe, e.g. 1h, 15m, 5m')
    parser.add_argument('--signal_timeframe', default=None,
                        help='Signal/model timeframe. Use 1h with 15m/5m execution for MTF mode.')
    parser.add_argument('--mode', default='advanced', choices=['advanced', 'wright'],
                        help='Which engine to run: advanced (default) or wright (from website)')
    args = parser.parse_args()

    if args.mode == 'wright':
        engine = importlib.import_module('phase_10.wright_engine')
        results_file = RESULTS_WRIGHT_FILE
    else:
        engine = importlib.import_module('phase_10.engine')
        results_file = RESULTS_FILE

    global run_pair_backtest
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
    print(f'TF     : signal={args.signal_timeframe or args.timeframe} execution={args.timeframe}')
    print(f'Pairs  : {len(pairs)} pairs')
    print('-' * 50)
    run_all(pairs, args.date_from, args.date_to, args.timeframe, args.signal_timeframe)


if __name__ == '__main__':
    main()
