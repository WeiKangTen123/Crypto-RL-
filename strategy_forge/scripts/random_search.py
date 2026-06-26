"""
random_search.py — randomly compose and backtest N strategy DNAs, save the best.

Usage
-----
python strategy_forge/scripts/random_search.py --coin BTCUSDT --tf 1h --n 200
python strategy_forge/scripts/random_search.py --coin ETHUSDT --tf 4h --n 500 --score roi
python strategy_forge/scripts/random_search.py --coin BTCUSDT --tf 1h --n 100 --top 20
"""
import os
import sys
import json
import argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest import load_data
from strategy_forge.composer.random_compose import random_population
from strategy_forge.runner.backtest_runner  import score_population

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')


def main():
    parser = argparse.ArgumentParser(description='Random strategy search')
    parser.add_argument('--coin',       default='BTCUSDT',    help='Coin symbol')
    parser.add_argument('--tf',         default='1h',         help='Timeframe')
    parser.add_argument('--date_from',  default='2022-01-01', help='Start date')
    parser.add_argument('--date_to',    default='2026-12-31', help='End date')
    parser.add_argument('--n',          type=int, default=100, help='Number of random strategies to test')
    parser.add_argument('--top',        type=int, default=10,  help='Number of top results to save')
    parser.add_argument('--score',      default='roi',         help='Scoring: roi | sharpe | blend')
    parser.add_argument('--min_trades', type=int, default=20,  help='Minimum trades to qualify')
    parser.add_argument('--max_filters',   type=int,   default=2,     help='Max filters per strategy (0-2)')
    parser.add_argument('--seed',          type=int,   default=42,    help='Random seed')
    parser.add_argument('--risk_per_trade',type=float, default=0.01,  help='Fraction of balance risked per trade')
    parser.add_argument('--leverage',      type=float, default=5.0,   help='Leverage multiplier')
    parser.add_argument('--style',         default=None,
                        choices=['hft', 'mft', 'swing'],
                        help='Trade style preset. Overrides min_trades/risk/leverage defaults. '
                             'hft=high-freq scalp (use hft_search.py for full HFT), '
                             'mft=medium-freq (default), swing=low-freq position.')
    args = parser.parse_args()

    # Apply style-based defaults (user explicit args still win via argparse ordering)
    if args.style == 'hft':
        if args.min_trades == 20:   args.min_trades    = 50
        if args.leverage   == 5.0:  args.leverage      = 3.0
        if args.risk_per_trade == 0.01: args.risk_per_trade = 0.005
        if args.max_filters == 2:   args.max_filters   = 1
    elif args.style == 'swing':
        if args.min_trades == 20:   args.min_trades    = 5
        if args.leverage   == 5.0:  args.leverage      = 3.0
        if args.risk_per_trade == 0.01: args.risk_per_trade = 0.02

    style_tag = f"  Style: {args.style.upper()}\n" if args.style else ''
    print(f"\n{'='*60}")
    print(f"  Strategy Forge — Random Search")
    print(f"  Coin: {args.coin}  TF: {args.tf}  N: {args.n}  Score: {args.score}")
    if style_tag:
        print(f"  Style: {args.style.upper()}  (min_trades={args.min_trades}  "
              f"leverage={args.leverage}x  risk={args.risk_per_trade})")
    print(f"{'='*60}\n")

    df = load_data(args.coin, args.tf, args.date_from, args.date_to)
    if df is None or df.empty:
        print('[ERROR] No data loaded.')
        sys.exit(1)

    print(f"Generating {args.n} random strategy DNAs...\n")
    population = random_population(df, size=args.n, seed=args.seed,
                                   max_filters=args.max_filters)

    risk_override = dict(risk_per_trade=args.risk_per_trade, leverage=args.leverage)
    print(f"Running backtests (risk_per_trade={args.risk_per_trade}, leverage={args.leverage})...\n")
    scored = score_population(population, df,
                              risk=risk_override,
                              score_mode=args.score,
                              min_trades=args.min_trades,
                              verbose=True)

    # Filter valid results
    valid = [(s, dna, m) for s, dna, m in scored if s > -999]
    print(f"\n{'='*60}")
    print(f"  Valid strategies: {len(valid)} / {args.n}")
    print(f"{'='*60}\n")

    if not valid:
        print('[WARN] No qualifying strategies found. Try lowering --min_trades.')
        sys.exit(0)

    top = valid[:args.top]
    print(f"  TOP {len(top)} RESULTS (by {args.score}):\n")
    for rank, (score, dna, m) in enumerate(top, 1):
        print(f"  #{rank:>2}  score={score:>8.2f}  "
              f"ROI={m.get('Total Return','?')}%  "
              f"Sharpe={m.get('Sharpe Ratio','?')}  "
              f"Trades={m.get('Total Trades','?')}  "
              f"MDD={m.get('Max Drawdown %','?')}%")
        print(f"       {dna.entry} + {dna.filters} → {dna.exit_method}")
        print(f"       params: {dna.params}")
        print()

    # Save to JSON
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(RESULTS_DIR, f'random_search_{args.coin}_{args.tf}_{ts}.json')

    output = {
        'run_at':      datetime.now().isoformat(),
        'style':       args.style or 'generic',
        'coin':        args.coin,
        'tf':          args.tf,
        'date_from':   args.date_from,
        'date_to':     args.date_to,
        'n_tested':    args.n,
        'score_mode':  args.score,
        'n_valid':     len(valid),
        'top_results': [
            {
                'rank':       rank,
                'score':      score,
                'entry':      dna.entry,
                'filters':    dna.filters,
                'exit_method':dna.exit_method,
                'params':     dna.params,
                'metrics': {
                    'total_return':    m.get('Total Return'),
                    'sharpe':          m.get('Sharpe Ratio'),
                    'max_drawdown':    m.get('Max Drawdown %'),
                    'win_rate':        m.get('Win Rate'),
                    'total_trades':    m.get('Total Trades'),
                    'profit_factor':   m.get('Profit Factor'),
                    'trades_per_week': m.get('trades_per_week'),
                    'style':           m.get('style'),
                },
            }
            for rank, (score, dna, m) in enumerate(top, 1)
        ],
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {out_path}")


if __name__ == '__main__':
    main()
