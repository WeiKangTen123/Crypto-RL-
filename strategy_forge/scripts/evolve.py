"""
evolve.py — genetic algorithm evolution loop over StrategyDNA population.

Starts with a random population, then evolves across N generations,
keeping top survivors and breeding children each round.

Usage
-----
python strategy_forge/scripts/evolve.py --coin BTCUSDT --tf 1h --generations 10
python strategy_forge/scripts/evolve.py --coin ETHUSDT --tf 4h --pop 60 --generations 20 --score blend
"""
import os
import sys
import json
import argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest        import load_data
from strategy_forge.composer.random_compose import random_population
from strategy_forge.composer.genetic        import evolve
from strategy_forge.runner.backtest_runner  import score_population

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')


def main():
    parser = argparse.ArgumentParser(description='Genetic evolution of strategy DNAs')
    parser.add_argument('--coin',        default='BTCUSDT',    help='Coin symbol')
    parser.add_argument('--tf',          default='1h',         help='Timeframe')
    parser.add_argument('--date_from',   default='2022-01-01')
    parser.add_argument('--date_to',     default='2026-12-31')
    parser.add_argument('--pop',         type=int, default=50,  help='Initial population size')
    parser.add_argument('--generations', type=int, default=10,  help='Number of generations')
    parser.add_argument('--survivors',   type=int, default=10,  help='Top survivors per generation')
    parser.add_argument('--offspring',   type=int, default=30,  help='Children per generation')
    parser.add_argument('--mutation',    type=float, default=0.2, help='Mutation rate (0.0–1.0)')
    parser.add_argument('--score',       default='blend',       help='roi | sharpe | blend')
    parser.add_argument('--min_trades',  type=int, default=20)
    parser.add_argument('--seed',        type=int, default=42)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Strategy Forge — Genetic Evolution")
    print(f"  Coin: {args.coin}  TF: {args.tf}")
    print(f"  Pop: {args.pop}  Generations: {args.generations}  Score: {args.score}")
    print(f"{'='*60}\n")

    df = load_data(args.coin, args.tf, args.date_from, args.date_to)
    if df is None or df.empty:
        print('[ERROR] No data loaded.')
        sys.exit(1)

    # Generation 0 — random seed population
    print(f"[Gen 0] Generating random population ({args.pop})...\n")
    population = random_population(df, size=args.pop, seed=args.seed)
    scored = score_population(population, df,
                              score_mode=args.score,
                              min_trades=args.min_trades,
                              verbose=True)

    best_ever = []
    hall_of_fame = []   # running top results across all generations

    for gen in range(1, args.generations + 1):
        valid = [(s, dna, m) for s, dna, m in scored if s > -999]
        top3  = valid[:3]

        print(f"\n{'─'*60}")
        print(f"  [Gen {gen-1}] Valid: {len(valid)}/{len(scored)}  "
              f"Best score: {top3[0][0] if top3 else 'N/A'}")
        if top3:
            s, dna, m = top3[0]
            print(f"  Best: {dna.entry} + {dna.filters} → {dna.exit_method}")
            print(f"        ROI={m.get('Total Return','?')}%  "
                  f"Sharpe={m.get('Sharpe Ratio','?')}  "
                  f"Trades={m.get('Total Trades','?')}")

        # Accumulate hall of fame
        hall_of_fame.extend([(s, dna.to_dict(), m) for s, dna, m in valid])
        hall_of_fame.sort(key=lambda x: x[0], reverse=True)
        hall_of_fame = hall_of_fame[:20]   # keep all-time top 20

        # Evolve to next generation
        scored_pairs = [(s, dna) for s, dna, _ in scored]
        new_pop = evolve(
            scored_pairs, df,
            n_survivors=args.survivors,
            n_offspring=args.offspring,
            mutation_rate=args.mutation,
            seed=args.seed + gen,
        )

        print(f"\n[Gen {gen}] Backtesting {len(new_pop)} strategies...\n")
        scored = score_population(new_pop, df,
                                  score_mode=args.score,
                                  min_trades=args.min_trades,
                                  verbose=True)

    # Final output
    print(f"\n{'='*60}")
    print(f"  HALL OF FAME — Top {min(10, len(hall_of_fame))} across all generations")
    print(f"{'='*60}\n")
    for rank, (score, dna_d, m) in enumerate(hall_of_fame[:10], 1):
        print(f"  #{rank:>2}  score={score:>8.2f}  "
              f"ROI={m.get('Total Return','?')}%  "
              f"Sharpe={m.get('Sharpe Ratio','?')}  "
              f"Trades={m.get('Total Trades','?')}")
        print(f"       {dna_d['entry']} + {dna_d['filters']} → {dna_d['exit_method']}")
        print()

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(RESULTS_DIR, f'evolve_{args.coin}_{args.tf}_{ts}.json')

    output = {
        'run_at':      datetime.now().isoformat(),
        'coin':        args.coin,
        'tf':          args.tf,
        'date_from':   args.date_from,
        'date_to':     args.date_to,
        'generations': args.generations,
        'pop_size':    args.pop,
        'score_mode':  args.score,
        'hall_of_fame': [
            {
                'rank':       rank,
                'score':      score,
                'entry':      d['entry'],
                'filters':    d['filters'],
                'exit_method':d['exit_method'],
                'params':     d['params'],
                'metrics': {
                    'total_return':  m.get('Total Return'),
                    'sharpe':        m.get('Sharpe Ratio'),
                    'max_drawdown':  m.get('Max Drawdown %'),
                    'win_rate':      m.get('Win Rate'),
                    'total_trades':  m.get('Total Trades'),
                    'profit_factor': m.get('Profit Factor'),
                },
            }
            for rank, (score, d, m) in enumerate(hall_of_fame, 1)
        ],
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {out_path}")


if __name__ == '__main__':
    main()
