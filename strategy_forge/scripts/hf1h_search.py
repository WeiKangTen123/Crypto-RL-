"""
hf1h_search.py — High-frequency 1h strategy discovery.

Target: Monthly ROI 1.8–4.0% | MDD ≤25% | Sharpe 1.0–2.5
Frequency: ≥10 trades/month per coin (active in all periods including 2026)
Exit sweep: tries all 6 swing exits per top strategy × coin combo.

Usage:
  python strategy_forge/scripts/hf1h_search.py --n 500 --coins all
  python strategy_forge/scripts/hf1h_search.py --n 400 --coins all --generations 10
"""
import os, sys, json, math, random, argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest         import load_data
from strategy_forge.composer.dna            import StrategyDNA
from strategy_forge.composer.random_compose import random_dna, _ENTRY_PARAMS, _FILTER_PARAMS, _EXIT_PARAMS
from strategy_forge.runner.backtest_runner  import score_dna, DEFAULT_RISK
from strategy_backtest.metrics              import compute_metrics, _extract_numeric
from strategy_backtest.engine               import BacktestEngine
from strategy_backtest.risk                 import RiskManager

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')

ALL_COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'AVAX', 'LINK', 'ADA', 'MATIC', 'DOT']
SAFE_COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'AVAX', 'LINK', 'ADA', 'DOT']  # no MATIC

TF = '1h'
TF_HIERARCHY = {'htf1': 4, 'htf2': 24, 'macro': 168}

# Entry pool for 1h — swing signals that fire ≥10x/month
HF_ENTRIES = [
    'macd_cross', 'ema_cross', 'hma_cross', 'zlema_cross',
    'bb_breakout', 'supertrend', 'aroon_cross', 'vortex_cross',
    'elder_ray', 'cvd_cross', 'wavetrend', 'zscore_reversion',
    'zscore_ema',
]

# All exits to try in Phase 3 sweep
SWING_EXITS = ['psar_trail', 'atr_tp_sl', 'trailing_tp', 'chandelier', 'supertrend_trail', 'rr_ratio']

# Discovery target (multi-coin aggregate)
TARGET_SHARPE_MIN  = 1.0    # minimum Sharpe — no upper cap (higher is better)
TARGET_MDD_MAX     = 20.0
TARGET_MONTHLY_MIN = 2.0
TARGET_MONTHLY_MAX = 3.5    # soft cap — relax slightly so we don't miss 3.x%
MIN_TRADES_MULTI   = 50     # just reject dead strategies; per-coin filter is in Phase 3
# Per-coin frequency filter (applied in Phase 3)
MIN_TRADES_PM      = 8.0    # trades per month per coin (≈1 per 3-4 days, lenient floor)
MIN_EXITS_2026     = 3      # must be active in 2026

DATE_FROM = '2024-01-01'
DATE_TO   = '2026-05-31'
MONTHS    = 28.0


def monthly_roi(annual_pct):
    return ((1 + annual_pct / 100) ** (1/12) - 1) * 100


def passes_target(nm):
    sh  = nm.get('Sharpe Ratio', 0)
    mdd = abs(nm.get('Max Drawdown %', 999))
    mo  = nm.get('monthly_roi', 0)
    tr  = nm.get('Total Trades', 0)
    return (sh >= TARGET_SHARPE_MIN and
            mdd <= TARGET_MDD_MAX and
            TARGET_MONTHLY_MIN <= mo <= TARGET_MONTHLY_MAX and
            tr >= MIN_TRADES_MULTI)


def blend_score(nm):
    sh  = nm.get('Sharpe Ratio', 0)
    roi = nm.get('Total Return', 0)
    return round(0.5 * sh + 0.5 * math.copysign(math.log1p(abs(roi) / 25.0), roi), 4)


def enrich(nm):
    ann = nm.get('Annual Return', nm.get('Total Return', 0))
    if isinstance(ann, str):
        try: ann = float(ann.replace('%', ''))
        except: ann = 0.0
    nm['monthly_roi']  = monthly_roi(ann)
    nm['blend_score']  = blend_score(nm)
    return nm


def run_multicoin(dna, data, risk):
    r = {**DEFAULT_RISK, **risk}
    score, nm = score_dna(dna, data, risk=r, score_mode='blend',
                          min_trades=MIN_TRADES_MULTI)
    if score <= -900 or not nm:
        return None
    return enrich(nm)


def coin_backtest(entry, filters, exit_m, params, df, risk):
    r = {**DEFAULT_RISK, **risk}
    try:
        dna = StrategyDNA(df, entry=entry, filters=filters,
                          exit_method=exit_m, params=params)
        rm  = RiskManager(risk_per_trade=r['risk_per_trade'],
                          leverage=r['leverage'],
                          trading_fee=0.0004,
                          maintenance_margin_rate=0.005)
        eng   = BacktestEngine(df, dna, rm, initial_balance=10000)
        equity = eng.run()
        nm    = _extract_numeric(compute_metrics(
            equity, 10000, timestamps=df.index, trades=eng.trades))
        ann   = nm.get('Annual Return', 0)
        mo    = monthly_roi(ann)
        trades = nm.get('Total Trades', 0)
        e26   = len([t for t in eng.trades
                     if t['type'] in ('EXIT_LONG','EXIT_SHORT')
                     and str(t['time']) >= '2026'])
        return dict(
            sharpe=nm.get('Sharpe Ratio', 0),
            mdd=abs(nm.get('Max Drawdown %', 99)),
            monthly=mo,
            annual=ann,
            total_return=nm.get('Total Return', 0),
            trades=trades,
            trades_pm=trades / MONTHS,
            win_rate=nm.get('Win Rate', 0),
            exits_2026=e26,
        )
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coins',          default='all')
    parser.add_argument('--n',              type=int,   default=500)
    parser.add_argument('--generations',    type=int,   default=10)
    parser.add_argument('--offspring',      type=int,   default=50)
    parser.add_argument('--date_from',      default=DATE_FROM)
    parser.add_argument('--date_to',        default=DATE_TO)
    parser.add_argument('--risk_per_trade', type=float, default=0.05)
    parser.add_argument('--leverage',       type=float, default=5.0)
    parser.add_argument('--seed',           type=int,   default=42)
    parser.add_argument('--top',            type=int,   default=30)
    args = parser.parse_args()

    rng  = random.Random(args.seed)
    risk = dict(risk_per_trade=args.risk_per_trade, leverage=args.leverage)

    coins = SAFE_COINS if args.coins == 'all' else [c.strip().upper() for c in args.coins.split(',')]

    print('=' * 68)
    print('  HF-1H Strategy Forge — 1h High-Frequency Discovery')
    print(f'  Coins: {coins}')
    print(f'  Target: Sharpe ≥{TARGET_SHARPE_MIN} (no cap) | MDD≤{TARGET_MDD_MAX}%'
          f' | Monthly {TARGET_MONTHLY_MIN}–{TARGET_MONTHLY_MAX}%')
    print(f'  Freq: ≥{MIN_TRADES_PM} trades/coin/month | ≥{MIN_EXITS_2026} exits in 2026')
    print(f'  Risk: {args.risk_per_trade} per trade | {args.leverage}x leverage')
    print('=' * 68)

    # ── Load data ─────────────────────────────────────────────────────────────
    data = {}
    for coin in coins:
        try:
            df = load_data(coin, TF, args.date_from, args.date_to)
            data[coin] = df
            print(f'  Loaded {coin} 1h: {len(df):,} bars')
        except Exception as e:
            print(f'  SKIP {coin}: {e}')

    df_sample = next(iter(data.values()))

    # ── Phase 1: Random search ────────────────────────────────────────────────
    print(f'\n[Phase 1] Random search ({args.n} candidates, HF entry pool)...')
    scored = []
    hits   = 0
    for i in range(args.n):
        seed_i = rng.randint(0, 999999)
        exit_m = rng.choice(SWING_EXITS)
        entry  = rng.choice(HF_ENTRIES)
        try:
            dna = random_dna(df_sample, seed=seed_i,
                             entry=entry, exit_method=exit_m, max_filters=2)
            # Force HTF bars to match 1h hierarchy
            dna.params.update({
                'htf_bars':  TF_HIERARCHY['htf1'],
                'htf1_bars': TF_HIERARCHY['htf1'],
                'htf2_bars': TF_HIERARCHY['htf2'],
                'macro_bars': TF_HIERARCHY['macro'],
            })
            nm = run_multicoin(dna, data, risk)
            if nm is None:
                continue
            scored.append((nm['blend_score'], dna, nm))
            if passes_target(nm):
                hits += 1
        except Exception:
            continue

        if (i + 1) % 100 == 0:
            bsh = max((x[2].get('Sharpe Ratio',0) for x in scored), default=0)
            bmo = max((x[2].get('monthly_roi', 0) for x in scored), default=0)
            print(f'  {i+1}/{args.n}  hits={hits}  best_sharpe={bsh:.2f}  best_monthly={bmo:.2f}%')

    scored.sort(key=lambda x: -x[0])
    print(f'  Phase 1 done: {len(scored)} valid | {hits} hit target')

    # ── Phase 2: Genetic evolution ────────────────────────────────────────────
    print(f'\n[Phase 2] Genetic evolution ({args.generations} gen × {args.offspring} offspring)...')

    # Prioritise strategies that already hit the target in Phase 1 — prevents
    # high-blend-score but out-of-range "monsters" from crowding out good seeds.
    target_hits_pool = [x for x in scored if passes_target(x[2])]
    others_pool      = [x for x in scored if not passes_target(x[2])]
    top_pool = (target_hits_pool + others_pool)[:30]

    for gen in range(args.generations):
        gen_scored = []
        for _ in range(args.offspring):
            p1 = rng.choice(top_pool[:10])
            p2 = rng.choice(top_pool[:15])
            d1, d2 = p1[1], p2[1]

            # Crossover params
            child_params = {}
            for k in d1.params:
                child_params[k] = d1.params[k] if rng.random() < 0.5 else d2.params.get(k, d1.params[k])

            # Mutate a fraction
            for k in list(child_params.keys()):
                if rng.random() < 0.15:
                    v = child_params[k]
                    if isinstance(v, int):
                        child_params[k] = max(2, v + rng.randint(-15, 15))
                    else:
                        child_params[k] = round(v * rng.uniform(0.75, 1.25), 4)

            # Force HTF
            child_params.update({
                'htf_bars':  TF_HIERARCHY['htf1'],
                'htf1_bars': TF_HIERARCHY['htf1'],
                'htf2_bars': TF_HIERARCHY['htf2'],
                'macro_bars': TF_HIERARCHY['macro'],
            })

            # Choose entry / filters / exit
            entry   = d1.entry   if rng.random() < 0.75 else rng.choice(HF_ENTRIES)
            filters = d1.filters if rng.random() < 0.70 else d2.filters
            exit_m  = d1.exit_method if rng.random() < 0.65 else rng.choice(SWING_EXITS)

            try:
                child_dna = StrategyDNA(df_sample, entry=entry, filters=filters,
                                        exit_method=exit_m, params=child_params)
                nm = run_multicoin(child_dna, data, risk)
                if nm is None:
                    continue
                sc = nm['blend_score']
                gen_scored.append((sc, child_dna, nm))
            except Exception:
                continue

        # Merge: keep target-hits first, fill rest by blend_score
        all_pool = top_pool + gen_scored
        gen_target = [x for x in all_pool if passes_target(x[2])]
        gen_others = [x for x in all_pool if not passes_target(x[2])]
        gen_others.sort(key=lambda x: -x[0])
        top_pool = (gen_target + gen_others)[:30]

        gen_hits = sum(1 for _, _, nm in gen_scored if passes_target(nm))
        best = gen_scored[0][2] if gen_scored else {}
        print(f'  [Gen {gen+1}] Sharpe={best.get("Sharpe Ratio",0):.2f} '
              f'Mo={best.get("monthly_roi",0):.2f}%  '
              f'MDD={abs(best.get("Max Drawdown %",0)):.1f}%  hits={gen_hits}')

    print(f'  Phase 2 done.')

    # ── Phase 3: Per-coin × exit sweep ───────────────────────────────────────
    print(f'\n[Phase 3] Per-coin × exit sweep (top {min(args.top, len(top_pool))} candidates × {len(coins)} coins × {len(SWING_EXITS)} exits)...')

    final_hits = []
    seen = set()

    for rank_idx, (_, base_dna, _) in enumerate(top_pool[:args.top]):
        entry   = base_dna.entry
        filters = base_dna.filters
        base_params = dict(base_dna.params)

        for exit_m in SWING_EXITS:
            params = dict(base_params)
            for coin, df in data.items():
                key = (entry, tuple(sorted(filters)), exit_m, coin)
                if key in seen:
                    continue
                cm = coin_backtest(entry, filters, exit_m, params, df, risk)
                if cm is None:
                    continue
                sh  = cm['sharpe']
                mdd = cm['mdd']
                mo  = cm['monthly']
                tpm = cm['trades_pm']
                e26 = cm['exits_2026']
                if (sh >= TARGET_SHARPE_MIN and
                        mdd <= TARGET_MDD_MAX and
                        TARGET_MONTHLY_MIN <= mo <= TARGET_MONTHLY_MAX and
                        tpm >= MIN_TRADES_PM and e26 >= MIN_EXITS_2026):
                    seen.add(key)
                    final_hits.append({
                        'coin': coin, 'exit': exit_m, 'entry': entry,
                        'filters': filters, 'params': params,
                        'sharpe': sh, 'mdd': mdd, 'monthly': mo,
                        'trades_pm': tpm, 'exits_2026': e26,
                        'annual': cm['annual'], 'total_return': cm['total_return'],
                        'win_rate': cm['win_rate'],
                    })

    def fit(h):
        # Closeness to target: monthly 2.5% center, Sharpe≥1.0, freq≥10/mo
        mo_score = max(0, 1 - abs(h['monthly'] - 2.5) / 2.0)
        sh_score = min(1, h['sharpe'] / 2.0)
        fr_score = min(1, h['trades_pm'] / 15.0)
        return mo_score + sh_score + fr_score

    final_hits.sort(key=fit, reverse=True)

    print(f'\n  === HITS: {len(final_hits)} strategies pass all constraints ===\n')
    if final_hits:
        print('  %-6s %-7s %-5s %-5s %-6s %-5s  %-12s  %-20s  Filters' % (
            'Coin','Sharpe','MDD%','Mo%','Tr/Mo','2026','Exit','Entry'))
        print('  ' + '-'*100)
        for i, h in enumerate(final_hits[:25]):
            print('  %-6s %7.2f %5.1f %5.2f %6.1f %5d  %-12s  %-20s  %s' % (
                h['coin'], h['sharpe'], h['mdd'], h['monthly'],
                h['trades_pm'], h['exits_2026'], h['exit'], h['entry'],
                str(h['filters'])))

    # ── Save ─────────────────────────────────────────────────────────────────
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    out_path = os.path.join(RESULTS_DIR, f'hf1h_search_{ts}.json')
    out = {
        'run_at':    datetime.now().isoformat(),
        'tf':        TF,
        'coins':     coins,
        'date_from': args.date_from,
        'date_to':   args.date_to,
        'risk':      risk,
        'n_hits':    len(final_hits),
        'results':   [
            {**{k: h[k] for k in ['coin','entry','filters','exit','params',
                                   'sharpe','monthly','mdd','trades_pm',
                                   'exits_2026','annual','total_return','win_rate']},
             'tf': TF, 'rank': i+1}
            for i, h in enumerate(final_hits[:args.top])
        ]
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'\n  Saved → {out_path}')
    return out_path


if __name__ == '__main__':
    main()
