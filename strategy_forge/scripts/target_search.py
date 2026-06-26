"""
target_search.py — Find strategies matching a specific performance target.

Runs a large random population + genetic evolution, then filters results
by Sharpe, MDD, and monthly ROI targets.

Usage
-----
python strategy_forge/scripts/target_search.py --coin ETH --tf 4h
python strategy_forge/scripts/target_search.py --coin BTC --tf 1h --n 400
"""
import os, sys, json, argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest     import load_data
from strategy_forge.composer.random_compose import random_population
from strategy_forge.composer.genetic    import evolve
from strategy_forge.runner.backtest_runner  import score_dna, DEFAULT_RISK
from strategy_backtest.metrics          import compute_metrics, _extract_numeric
from strategy_backtest.engine           import BacktestEngine
from strategy_backtest.risk             import RiskManager
from strategy_forge.composer.dna        import StrategyDNA

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')

TARGET = dict(
    sharpe_min   = 1.0,
    sharpe_max   = 2.5,
    mdd_max      = 25.0,   # %
    monthly_min  = 1.8,    # % per month
    monthly_max  = 4.0,    # % per month
    min_trades   = 50,
)


def monthly_roi(annual_pct: float) -> float:
    return ((1 + annual_pct / 100) ** (1/12) - 1) * 100


def score_and_metrics(dna, df, risk):
    """Run full backtest and return (score, numeric_metrics, annual_return)."""
    r = {**DEFAULT_RISK, **risk}
    dna_copy = StrategyDNA(df.copy(), dna.entry, dna.filters, dna.exit_method, dna.params)
    try:
        rm = RiskManager(
            risk_per_trade=r['risk_per_trade'],
            leverage=r['leverage'],
            trading_fee=r['trading_fee'],
            slippage_pct=r['slippage_pct'],
            maintenance_margin_rate=r['maintenance_margin_rate'],
        )
        engine = BacktestEngine(df.copy(), dna_copy, rm, initial_balance=r['initial_balance'])
        equity = engine.run()
        if not equity or len(equity) < 2:
            return None
        m  = compute_metrics(equity, r['initial_balance'],
                             timestamps=engine.df.index, trades=engine.trades)
        nm = _extract_numeric(m)
        # Get annual return for monthly calculation
        annual_str = m.get('Annual Return', '0%')
        annual = float(str(annual_str).replace('%',''))
        nm['annual_return'] = annual
        nm['monthly_roi']   = monthly_roi(annual)
        return nm
    except Exception:
        return None


def passes_target(nm: dict) -> bool:
    t = TARGET
    sharpe  = nm.get('Sharpe Ratio', 0)
    mdd     = abs(nm.get('Max Drawdown %', 999))
    trades  = nm.get('Total Trades', 0)
    monthly = nm.get('monthly_roi', 0)
    return (
        t['sharpe_min'] <= sharpe <= t['sharpe_max'] and
        mdd <= t['mdd_max'] and
        t['monthly_min'] <= monthly <= t['monthly_max'] and
        trades >= t['min_trades']
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coin',       default='ETH')
    parser.add_argument('--tf',         default='4h')
    parser.add_argument('--date_from',  default='2022-01-01')
    parser.add_argument('--date_to',    default='2026-06-01')
    parser.add_argument('--n',          type=int, default=300)
    parser.add_argument('--generations',type=int, default=8)
    parser.add_argument('--survivors',  type=int, default=15)
    parser.add_argument('--offspring',  type=int, default=40)
    parser.add_argument('--risk_per_trade', type=float, default=0.05)
    parser.add_argument('--leverage',   type=float, default=5.0)
    parser.add_argument('--seed',       type=int,  default=42)
    parser.add_argument('--max_filters',type=int,  default=2)
    args = parser.parse_args()

    # Dataset uses bare coin names (ETH, BTC) — strip USDT suffix if present
    coin_sym = args.coin.replace('USDT', '') if args.coin.endswith('USDT') else args.coin
    risk = dict(risk_per_trade=args.risk_per_trade, leverage=args.leverage)

    print(f"\n{'='*65}")
    print(f"  Target Forge Search — {args.coin} {args.tf}")
    print(f"  Target: Sharpe {TARGET['sharpe_min']}–{TARGET['sharpe_max']} | "
          f"MDD ≤{TARGET['mdd_max']}% | Monthly {TARGET['monthly_min']}–{TARGET['monthly_max']}%")
    print(f"  N={args.n} random + {args.generations} generations evolve")
    print(f"{'='*65}\n")

    df = load_data(coin_sym, args.tf, args.date_from, args.date_to)
    if df is None or df.empty:
        print('[ERROR] No data.'); sys.exit(1)

    hits = []

    # ── Phase 1: Random population ────────────────────────────────────────────
    print(f"[Phase 1] Random search ({args.n} candidates)...\n")
    population = random_population(df, size=args.n, seed=args.seed,
                                   max_filters=args.max_filters)

    phase1_scored = []
    for i, dna in enumerate(population):
        nm = score_and_metrics(dna, df, risk)
        if nm is None:
            continue
        score = 0.5 * nm.get('Sharpe Ratio', 0) + 0.5 * nm.get('monthly_roi', 0) / 3.0
        phase1_scored.append((score, dna, nm))
        if passes_target(nm):
            hits.append((dna, nm))
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{args.n} done — hits so far: {len(hits)}")

    phase1_scored.sort(key=lambda x: x[0], reverse=True)
    print(f"\n[Phase 1] Done. Hits: {len(hits)}")

    # ── Phase 2: Evolve top survivors ─────────────────────────────────────────
    print(f"\n[Phase 2] Evolving top {args.survivors} across {args.generations} generations...\n")
    # evolve() expects list of (score, dna) tuples
    scored_tuples = [(sc, d) for sc, d, _ in phase1_scored[:args.survivors]]

    for gen in range(1, args.generations + 1):
        children = evolve(scored_tuples, df, n_offspring=args.offspring,
                          mutation_rate=0.25, seed=args.seed + gen)
        gen_scored = []
        for dna in children:
            nm = score_and_metrics(dna, df, risk)
            if nm is None:
                continue
            score = 0.5 * nm.get('Sharpe Ratio', 0) + 0.5 * nm.get('monthly_roi', 0) / 3.0
            gen_scored.append((score, dna, nm))
            if passes_target(nm):
                hits.append((dna, nm))

        gen_scored.sort(key=lambda x: x[0], reverse=True)
        scored_tuples = [(sc, d) for sc, d, _ in gen_scored[:args.survivors]]
        hit_count = sum(1 for _, nm in hits if passes_target(nm))
        best_sh = gen_scored[0][2].get('Sharpe Ratio', 0) if gen_scored else 0
        print(f"  [Gen {gen}] Best Sharpe={best_sh:.2f} | Total target hits: {len(hits)}")

    # ── Deduplicate & rank hits ───────────────────────────────────────────────
    seen = set()
    unique_hits = []
    for dna, nm in hits:
        key = (dna.entry, tuple(sorted(dna.filters)), dna.exit_method)
        if key not in seen:
            seen.add(key)
            unique_hits.append((dna, nm))

    unique_hits.sort(key=lambda x: (
        -x[1].get('Sharpe Ratio', 0) * 0.5
        - x[1].get('monthly_roi', 0) / 3.0 * 0.3
        + x[1].get('Max Drawdown %', 99) / 100 * 0.2
    ))

    print(f"\n{'='*65}")
    print(f"  RESULTS — {len(unique_hits)} unique strategies hit target")
    print(f"{'='*65}")

    output = []
    for rank, (dna, nm) in enumerate(unique_hits[:20], 1):
        sharpe  = nm.get('Sharpe Ratio', 0)
        mdd     = abs(nm.get('Max Drawdown %', 0))
        monthly = nm.get('monthly_roi', 0)
        trades  = nm.get('Total Trades', 0)
        wr      = nm.get('Win Rate', 0)
        pf      = nm.get('Profit Factor', 0)
        annual  = nm.get('annual_return', 0)

        print(f"\n  #{rank}  Entry={dna.entry}  Filters={dna.filters}  Exit={dna.exit_method}")
        print(f"       Sharpe={sharpe:.2f}  Monthly={monthly:.2f}%  Annual={annual:.1f}%"
              f"  MDD={mdd:.1f}%  WR={wr:.1f}%  Trades={trades}  PF={pf:.2f}")
        print(f"       Params: {json.dumps(dna.params, default=str)[:120]}")

        output.append({
            'rank':   rank,
            'coin':   args.coin,
            'tf':     args.tf,
            'entry':  dna.entry,
            'filters': dna.filters,
            'exit':   dna.exit_method,
            'params': dna.params,
            'sharpe': round(sharpe, 3),
            'monthly_roi': round(monthly, 2),
            'annual_return': round(annual, 2),
            'mdd':    round(mdd, 2),
            'win_rate': round(wr, 2),
            'trades': int(trades),
            'profit_factor': round(pf, 3),
        })

    # Save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts   = datetime.now().strftime('%Y%m%d_%H%M')
    path = os.path.join(RESULTS_DIR, f'target_hits_{args.coin}_{args.tf}_{ts}.json')
    with open(path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved {len(output)} hits → {path}")


if __name__ == '__main__':
    main()
