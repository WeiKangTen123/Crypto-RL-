"""
Phase 11 — Anti-Correlation Crossover Backtest Runner

Usage:
  python phase_11/backtest.py
  python phase_11/backtest.py --pair BTC-ETH
  python phase_11/backtest.py --date_from 2023-01-01 --date_to 2026-05-31
"""

import os
import sys
import json
import argparse
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from phase_11.engine import (
    PAIRS, DATE_FROM, DATE_TO, TIMEFRAME, TIMEFRAME_MINUTES,
    run_pair_backtest,
)

DATASET_DIR  = os.path.join(_ROOT, 'dataset')
RESULTS_FILE = os.path.join(_ROOT, 'phase_11', 'data', 'results.json')


def run_all(pairs, date_from, date_to, timeframe):
    results = []
    total   = len(pairs)

    for idx, (coin_a, coin_b) in enumerate(pairs, 1):
        label = f'{coin_a}-{coin_b}'
        print(f'[{idx}/{total}] Running {label}...', flush=True)
        try:
            r = run_pair_backtest(coin_a, coin_b, DATASET_DIR, date_from, date_to, timeframe)
            trades = r.get('total_trades', 0)
            roi    = r.get('roi', 0)
            sharpe = r.get('sharpe', 0)
            wr     = r.get('win_rate', 0)
            corr   = r.get('avg_correlation', 0)
            print(f'  Trades={trades}  ROI={roi:+.2f}%  Sharpe={sharpe:.3f}  '
                  f'WR={wr:.1f}%  AvgCorr={corr:.3f}', flush=True)
        except Exception as e:
            print(f'  [ERROR] {e}', flush=True)
            r = {'pair': label, 'coin_a': coin_a, 'coin_b': coin_b,
                 'error': str(e), 'total_trades': 0, 'roi': 0.0}
        results.append(r)

    # Summary
    valid   = [r for r in results if 'error' not in r and r.get('total_trades', 0) > 0]
    total_roi = sum(r['roi'] for r in valid)
    total_trades = sum(r['total_trades'] for r in valid)
    print(f'\n{"─"*50}')
    print(f'TOTAL ROI  : {total_roi:+.2f}%')
    print(f'TOTAL TRADES: {total_trades}')
    print(f'{"─"*50}')

    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    output = {
        'generated_at': datetime.now().isoformat(),
        'strategy':     'phase_11_crossover',
        'date_from':    date_from,
        'date_to':      date_to,
        'timeframe':    timeframe,
        'summary': {
            'total_roi':    round(total_roi, 4),
            'total_trades': total_trades,
            'pairs_active': len(valid),
            'pairs_total':  len(results),
        },
        'pairs': results,
    }
    with open(RESULTS_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'Saved → {RESULTS_FILE}')
    return output


def main():
    parser = argparse.ArgumentParser(description='Phase 11 Crossover Backtest')
    parser.add_argument('--pair',      default=None,      help='Single pair e.g. BTC-ETH')
    parser.add_argument('--date_from', default=DATE_FROM, help='Start date YYYY-MM-DD')
    parser.add_argument('--date_to',   default=DATE_TO,   help='End date YYYY-MM-DD')
    parser.add_argument('--timeframe', default=TIMEFRAME,
                        choices=sorted(TIMEFRAME_MINUTES.keys()),
                        help='Timeframe (default: 1h)')
    args = parser.parse_args()

    if args.pair:
        parts = args.pair.split('-')
        if len(parts) != 2:
            print('ERROR: --pair must be COIN_A-COIN_B e.g. BTC-ETH')
            sys.exit(1)
        pairs = [(parts[0].upper(), parts[1].upper())]
    else:
        pairs = PAIRS

    print('Phase 11 — Anti-Correlation Crossover Backtest')
    print(f'Period    : {args.date_from} → {args.date_to}')
    print(f'Timeframe : {args.timeframe}')
    print(f'Pairs     : {len(pairs)}')
    print('─' * 50)
    run_all(pairs, args.date_from, args.date_to, args.timeframe)


if __name__ == '__main__':
    main()
