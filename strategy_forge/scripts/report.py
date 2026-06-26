"""
report.py — print a ranked summary from any saved random_search or evolve JSON.

Usage
-----
# Print latest result file automatically
python strategy_forge/scripts/report.py

# Print a specific file
python strategy_forge/scripts/report.py --file strategy_forge/results/random_search_BTCUSDT_1h_20260618_120000.json

# Show top N results
python strategy_forge/scripts/report.py --top 5
"""
import os
import sys
import json
import argparse
import glob
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')


def load_results(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def print_report(data: dict, top: int):
    print(f"\n{'='*70}")
    print(f"  Strategy Forge — Results Report")
    print(f"  File    : {data.get('run_at', '?')}")
    print(f"  Coin    : {data.get('coin')}   TF: {data.get('tf')}")
    print(f"  Period  : {data.get('date_from')} → {data.get('date_to')}")
    print(f"  Score   : {data.get('score_mode')}   "
          f"Tested: {data.get('n_tested', data.get('generations','?'))}")
    if 'n_valid' in data:
        print(f"  Valid   : {data['n_valid']} / {data.get('n_tested', '?')}")
    print(f"{'='*70}\n")

    key = 'top_results' if 'top_results' in data else 'hall_of_fame'
    results = data.get(key, [])[:top]

    if not results:
        print('  No results found.')
        return

    for r in results:
        m = r.get('metrics', {})
        print(f"  #{r['rank']:>2}  score={r['score']:>8.2f}")
        print(f"       Entry  : {r['entry']}")
        print(f"       Filters: {r.get('filters', [])}")
        print(f"       Exit   : {r['exit_method']}")
        print(f"       ROI    : {m.get('total_return', '?')}%   "
              f"Sharpe: {m.get('sharpe', '?')}   "
              f"MDD: {m.get('max_drawdown', '?')}%")
        print(f"       Trades : {m.get('total_trades', '?')}   "
              f"WinRate: {m.get('win_rate', '?')}%   "
              f"PF: {m.get('profit_factor', '?')}")
        print(f"       Params : {r.get('params', {})}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Print strategy_forge results report')
    parser.add_argument('--file', default=None, help='Path to result JSON (default: latest)')
    parser.add_argument('--top',  type=int, default=10, help='Show top N results')
    args = parser.parse_args()

    if args.file:
        path = os.path.join(ROOT, args.file) if not os.path.isabs(args.file) else args.file
    else:
        files = sorted(glob.glob(os.path.join(RESULTS_DIR, '*.json')))
        if not files:
            print(f'[ERROR] No result files found in {RESULTS_DIR}')
            sys.exit(1)
        path = files[-1]
        print(f'Loading latest: {os.path.basename(path)}')

    data = load_results(path)
    print_report(data, args.top)


if __name__ == '__main__':
    main()
