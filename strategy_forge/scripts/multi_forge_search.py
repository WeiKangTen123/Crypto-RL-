"""
multi_forge_search.py — Multi-coin, multi-timeframe strategy discovery.

Architecture: LTF entry signal + dual-HTF regime filter + macro regime guard.
  5m  base : HTF1=1h  (bars=12)  HTF2=4h  (bars=48)  Macro=1d  (bars=288)
  15m base : HTF1=1h  (bars=4)   HTF2=4h  (bars=16)  Macro=1d  (bars=96)
  1h  base : HTF1=4h  (bars=4)   HTF2=1d  (bars=24)  Macro=1w  (bars=168)
  4h  base : HTF1=1d  (bars=6)   HTF2=1w  (bars=42)
  1d  base : HTF1=1w  (bars=7)   (no macro needed)

Coins (10): BTC ETH BNB SOL XRP AVAX LINK ADA MATIC DOT

Scoring: blend = 0.5×Sharpe + 0.5×log1p(|ROI|/25)×sign
Target  : Sharpe ≥1.0,  MDD ≤25%,  Monthly ROI 1.8–4.0%

Usage
-----
# Run on all 10 coins at 1h with dual-HTF regime — recommended starting point
python strategy_forge/scripts/multi_forge_search.py --tf 1h --n 300 --coins all

# Sniper-swing: 5m entry with 1h+4h regime
python strategy_forge/scripts/multi_forge_search.py --tf 5m --n 400 --coins BTC,ETH,SOL

# Daily swing across all 10 coins
python strategy_forge/scripts/multi_forge_search.py --tf 4h --n 300 --coins all --score sharpe

# Run a specific coin set at a specific TF
python strategy_forge/scripts/multi_forge_search.py --tf 15m --coins BTC,ETH,BNB,SOL --n 200

# Full sweep: all TFs, all 10 coins (long — runs phases serially)
python strategy_forge/scripts/multi_forge_search.py --tf all --coins all --n 200
"""
import os, sys, json, argparse, math
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest         import load_data
from strategy_forge.composer.dna            import StrategyDNA
from strategy_forge.composer.random_compose import random_population
from strategy_forge.composer.genetic        import evolve
from strategy_forge.runner.backtest_runner  import score_dna, DEFAULT_RISK
from strategy_backtest.metrics              import compute_metrics, _extract_numeric
from strategy_backtest.engine               import BacktestEngine
from strategy_backtest.risk                 import RiskManager

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')

# ── Constants ─────────────────────────────────────────────────────────────────

ALL_COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'AVAX', 'LINK', 'ADA', 'MATIC', 'DOT']

ALL_TFS = ['5m', '15m', '1h', '4h', '1d']

# HTF hierarchy per base TF
TF_HIERARCHY = {
    '5m':  {'htf1': 12,  'htf2': 48,  'macro': 288},
    '15m': {'htf1': 4,   'htf2': 16,  'macro': 96},
    '1h':  {'htf1': 4,   'htf2': 24,  'macro': 168},
    '4h':  {'htf1': 6,   'htf2': 42,  'macro': None},
    '1d':  {'htf1': 7,   'htf2': None,'macro': None},
}

# Target performance criteria
TARGET = dict(sharpe_min=1.0, sharpe_max=2.5, mdd_max=25.0, monthly_min=1.8, monthly_max=4.0, min_trades=30)

# Entry signals well-suited to each timeframe category
TF_ENTRY_POOL = {
    'scalp':  ['stoch_rsi_reversion', 'williams_r_reversion', 'candle_engulfing',
               'candle_pin_bar', 'bb_reversion', 'wavetrend', 'vwap_reversion',
               'imbalance_zone', 'fvg_zone_touch', 'taker_momentum'],
    'swing':  ['ema_cross', 'hma_cross', 'zlema_cross', 'supertrend', 'aroon_cross',
               'vortex_cross', 'macd_cross', 'elder_ray', 'bb_breakout', 'fvg',
               'cvd_cross', 'zscore_reversion', 'zscore_ema'],
    'daily':  ['ema_cross', 'supertrend', 'macd_cross', 'rsi_trend', 'bb_breakout',
               'aroon_cross', 'elder_ray', 'hma_cross', 'vortex_cross'],
}

TF_STYLE = {
    '5m': 'scalp', '15m': 'scalp',
    '1h': 'swing', '4h': 'swing',
    '1d': 'daily',
}

# MTF exit methods (avoid pure time-stops for longer TFs)
TF_EXIT_POOL = {
    'scalp': ['atr_tp_sl_hold', 'breakeven_trail', 'tight_atr', 'rsi_exit', 'chandelier_tp'],
    'swing': ['atr_tp_sl', 'chandelier_tp', 'chandelier', 'supertrend_trail', 'trailing_tp', 'psar_trail'],
    'daily': ['chandelier', 'supertrend_trail', 'trailing_tp', 'atr_tp_sl'],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def monthly_roi(annual_pct: float) -> float:
    return ((1 + annual_pct / 100) ** (1/12) - 1) * 100


def passes_target(nm: dict) -> bool:
    t = TARGET
    return (
        t['sharpe_min']  <= nm.get('Sharpe Ratio', 0) <= t['sharpe_max'] and
        abs(nm.get('Max Drawdown %', 999)) <= t['mdd_max'] and
        t['monthly_min'] <= nm.get('monthly_roi', 0)        <= t['monthly_max'] and
        nm.get('Total Trades', 0) >= t['min_trades']
    )


def _blend_score(nm: dict) -> float:
    sh  = nm.get('Sharpe Ratio', 0)
    roi = nm.get('Total Return', 0)
    return round(0.5 * sh + 0.5 * math.copysign(math.log1p(abs(roi) / 25.0), roi), 4)


def _run_dna(dna: StrategyDNA, data: dict, risk: dict):
    """Run DNA on multi-coin data dict, return enriched metrics dict."""
    r = {**DEFAULT_RISK, **risk}
    # Use score_dna's multi-coin mode
    score, nm = score_dna(dna, data, risk=r, score_mode='blend', min_trades=TARGET['min_trades'])
    if score == -999.0 or not nm:
        return None
    # Enrich with monthly ROI
    annual = nm.get('Annual Return', nm.get('Total Return', 0))
    if isinstance(annual, str):
        try: annual = float(annual.replace('%', ''))
        except: annual = 0.0
    nm['annual_return'] = annual
    nm['monthly_roi']   = monthly_roi(annual)
    nm['blend_score']   = _blend_score(nm)
    return nm


def _make_mtf_dna(df_sample, entry: str, filters: list, exit_m: str, params: dict) -> StrategyDNA:
    return StrategyDNA(df_sample, entry=entry, filters=filters, exit_method=exit_m, params=params)


# ── Preset MTF candidates ─────────────────────────────────────────────────────

def _make_presets(tf: str, coin: str) -> list:
    """Hand-crafted MTF strategy presets for the given TF."""
    hier  = TF_HIERARCHY.get(tf, TF_HIERARCHY['1h'])
    htf1  = hier['htf1']
    htf2  = hier['htf2'] or htf1 * 4
    macro = hier['macro'] or htf2 * 4
    style = TF_STYLE.get(tf, 'swing')

    base_p = dict(
        htf1_bars=htf1, htf2_bars=htf2, macro_bars=macro,
        htf_bars=htf1, htf_ema_period=50, ema_trend_period=50,
        atr_period=14, tp_atr_mult=3.0, sl_atr_mult=1.0,
        adx_period=14, adx_threshold=25,
        st_period=10, st_multiplier=3.0,
        max_hold_bars=48, coin=coin,
    )

    presets = []
    # Preset A: EMA cross + dual-HTF regime + chandelier exit
    presets.append(dict(
        name='ema_dual_htf_chandelier',
        entry='ema_cross', filters=['dual_htf_trend', 'adx_trend'],
        exit='chandelier_tp',
        params={**base_p, 'ema_fast': 8, 'ema_slow': 21,
                'atr_multiplier': 3.0, 'tp_atr_mult': 4.0}
    ))
    # Preset B: Supertrend + macro regime + trailing TP
    presets.append(dict(
        name='supertrend_macro_trailing',
        entry='supertrend', filters=['macro_regime', 'atr_expansion'],
        exit='trailing_tp',
        params={**base_p, 'st_period': 10, 'st_multiplier': 3.0,
                'sl_atr_mult': 1.5, 'tp_activation_mult': 2.0, 'tp_trail_mult': 1.0}
    ))
    # Preset C: HMA cross + dual-HTF + ATR TP/SL
    presets.append(dict(
        name='hma_dual_htf_atr',
        entry='hma_cross', filters=['dual_htf_trend', 'obv_trend'],
        exit='atr_tp_sl',
        params={**base_p, 'ema_fast': 8, 'ema_slow': 34,
                'obv_period': 20, 'tp_atr_mult': 3.0, 'sl_atr_mult': 1.0}
    ))
    # Preset D: ZLEMA cross + dual-HTF + supertrend trail
    presets.append(dict(
        name='zlema_dual_htf_st_trail',
        entry='zlema_cross', filters=['dual_htf_trend', 'taker_confirm'],
        exit='supertrend_trail',
        params={**base_p, 'ema_fast': 13, 'ema_slow': 55,
                'intensity_period': 10, 'st_period': 10, 'st_multiplier': 2.5}
    ))
    # Preset E: BB breakout + macro regime + chandelier
    presets.append(dict(
        name='bb_breakout_macro_chandelier',
        entry='bb_breakout', filters=['macro_regime', 'vol_expansion'],
        exit='chandelier_tp',
        params={**base_p, 'bb_period': 20, 'bb_std': 2.0,
                'vol_ma_period': 20, 'vol_multiplier': 1.2,
                'atr_multiplier': 3.0, 'tp_atr_mult': 4.0}
    ))
    # Preset F: FVG + dual-HTF + ATR TP/SL (structure-based)
    presets.append(dict(
        name='fvg_dual_htf_atr',
        entry='fvg', filters=['dual_htf_trend', 'wr_not_extreme'],
        exit='atr_tp_sl',
        params={**base_p, 'tp_atr_mult': 3.0, 'sl_atr_mult': 0.8}
    ))
    # Preset G: CVD cross + macro + PSAR trail
    presets.append(dict(
        name='cvd_macro_psar',
        entry='cvd_cross', filters=['macro_regime', 'htf_ema_trend'],
        exit='psar_trail',
        params={**base_p, 'cvd_window': 20,
                'psar_acceleration': 0.02, 'psar_maximum': 0.2,
                'tp_atr_mult': 4.0}
    ))
    # Preset H: Elder Ray + dual-HTF + breakeven trail
    presets.append(dict(
        name='elder_ray_dual_htf_be',
        entry='elder_ray', filters=['dual_htf_trend', 'adx_trend'],
        exit='breakeven_trail',
        params={**base_p, 'period': 13, 'adx_period': 14, 'adx_threshold': 20,
                'sl_atr_mult': 1.0, 'be_trigger_mult': 1.5, 'atr_multiplier': 2.0}
    ))
    # Preset I: Stoch RSI + macro regime + tight ATR (scalp-oriented on lower TFs)
    if style == 'scalp':
        presets.append(dict(
            name='stochrsi_macro_tight_atr',
            entry='stoch_rsi_reversion', filters=['macro_regime', 'dual_htf_trend'],
            exit='tight_atr',
            params={**base_p, 'rsi_period': 14, 'smoothing': 3,
                    'rsi_oversold': 25, 'rsi_overbought': 75,
                    'sl_atr_mult': 0.6, 'tp_atr_mult': 2.5, 'max_hold_bars': 10}
        ))
        presets.append(dict(
            name='williams_macro_be',
            entry='williams_r_reversion', filters=['macro_regime', 'atr_expansion'],
            exit='breakeven_trail',
            params={**base_p, 'period': 14, 'sl_atr_mult': 0.8,
                    'be_trigger_mult': 1.2, 'atr_multiplier': 1.5, 'max_hold_bars': 12}
        ))
    # Preset J: IMB sniper + dual-HTF + atr_tp_sl (ultra-selective)
    presets.append(dict(
        name='imb_dual_htf_atr',
        entry='imbalance_zone', filters=['dual_htf_trend', 'taker_confirm'],
        exit='atr_tp_sl',
        params={**base_p, 'imb_threshold': 0.002, 'intensity_period': 10,
                'tp_atr_mult': 3.5, 'sl_atr_mult': 0.7}
    ))
    # Preset K: Aroon cross + macro regime + supertrend trail
    presets.append(dict(
        name='aroon_macro_st_trail',
        entry='aroon_cross', filters=['macro_regime', 'dual_htf_trend'],
        exit='supertrend_trail',
        params={**base_p, 'aroon_period': 25, 'aroon_threshold': 70,
                'st_period': 10, 'st_multiplier': 2.5}
    ))
    return presets


# ── Search phases ─────────────────────────────────────────────────────────────

def run_phase1_random(data: dict, n: int, tf: str, risk: dict, seed: int) -> list:
    """Random population — returns list of (blend_score, dna, nm)."""
    style   = TF_STYLE.get(tf, 'swing')
    entries = TF_ENTRY_POOL[style]
    exits   = TF_EXIT_POOL[style]

    # Use any coin's df as template for DNA construction
    df_sample = next(iter(data.values()))

    import random as _rnd
    from strategy_forge.composer.random_compose import _ENTRY_PARAMS, _FILTER_PARAMS, _EXIT_PARAMS
    from strategy_forge.params.ranges import sample_params
    from strategy_forge.signals.filter_signals import FILTER_REGISTRY

    rng = _rnd.Random(seed)
    hier = TF_HIERARCHY.get(tf, TF_HIERARCHY['1h'])
    mtf_filters = ['dual_htf_trend', 'macro_regime', 'htf_ema_trend', 'htf_supertrend']

    scored = []
    for i in range(n):
        entry_name = rng.choice(entries)
        exit_name  = rng.choice(exits)

        # Always include at least one MTF filter for regime awareness
        mtf_f = rng.choice(mtf_filters)
        # Optional second filter (non-MTF)
        non_mtf = [f for f in FILTER_REGISTRY if f not in mtf_filters]
        second_f = rng.choice(non_mtf) if rng.random() > 0.3 else None
        filters = [mtf_f] + ([second_f] if second_f else [])

        # Sample params
        param_names = (
            _ENTRY_PARAMS.get(entry_name, []) +
            sum([_FILTER_PARAMS.get(f, []) for f in filters], []) +
            _EXIT_PARAMS.get(exit_name, [])
        )
        params = sample_params(list(set(param_names)), seed=rng.randint(0, 2**31))
        # Pin HTF params to the correct hierarchy for this TF
        params['htf1_bars']  = hier['htf1']
        params['htf2_bars']  = hier.get('htf2') or hier['htf1'] * 4
        params['macro_bars'] = hier.get('macro') or (hier.get('htf2') or hier['htf1'] * 4) * 4
        params['htf_bars']   = hier['htf1']

        dna = StrategyDNA(df_sample, entry=entry_name, filters=filters,
                          exit_method=exit_name, params=params)
        nm  = _run_dna(dna, data, risk)
        if nm is None:
            continue
        scored.append((_blend_score(nm), dna, nm))

        if (i + 1) % 100 == 0:
            hits = sum(1 for _, _, m in scored if passes_target(m))
            print(f"    {i+1}/{n}  hits={hits}  best_sharpe={max((m.get('Sharpe Ratio',0) for _,_,m in scored), default=0):.2f}")

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def run_phase2_presets(data: dict, tf: str, coin: str, risk: dict) -> list:
    """Run hand-crafted MTF presets."""
    presets   = _make_presets(tf, coin)
    df_sample = next(iter(data.values()))
    scored    = []
    for p in presets:
        dna = StrategyDNA(df_sample, entry=p['entry'], filters=p['filters'],
                          exit_method=p['exit'], params=p['params'])
        nm  = _run_dna(dna, data, risk)
        if nm is None:
            continue
        sc  = _blend_score(nm)
        scored.append((sc, dna, nm))
        sh  = nm.get('Sharpe Ratio', 0)
        mo  = nm.get('monthly_roi', 0)
        mdd = nm.get('Max Drawdown %', 0)
        hit = '✓' if passes_target(nm) else ' '
        print(f"    {hit} {p['name']:<35} Sharpe={sh:.2f}  Mo={mo:.2f}%  MDD={mdd:.1f}%")
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def run_phase3_evolve(scored: list, data: dict, tf: str, risk: dict,
                      generations: int, n_offspring: int, seed: int) -> list:
    """Genetic evolution of top survivors."""
    df_sample = next(iter(data.values()))
    hier      = TF_HIERARCHY.get(tf, TF_HIERARCHY['1h'])
    all_hits  = []

    top_tuples = [(sc, dna) for sc, dna, _ in scored[:15]]

    for gen in range(1, generations + 1):
        children = evolve(top_tuples, df_sample,
                          n_offspring=n_offspring, mutation_rate=0.25,
                          seed=seed + gen)
        gen_scored = []
        for dna in children:
            # Re-pin HTF params after mutation
            dna.params['htf1_bars']  = hier['htf1']
            dna.params['htf2_bars']  = hier.get('htf2') or hier['htf1'] * 4
            dna.params['macro_bars'] = hier.get('macro') or (hier.get('htf2') or hier['htf1'] * 4) * 4
            dna.params['htf_bars']   = hier['htf1']

            nm = _run_dna(dna, data, risk)
            if nm is None:
                continue
            sc = _blend_score(nm)
            gen_scored.append((sc, dna, nm))
            if passes_target(nm):
                all_hits.append((sc, dna, nm))

        gen_scored.sort(key=lambda x: x[0], reverse=True)
        top_tuples = [(sc, dna) for sc, dna, _ in gen_scored[:15]]
        best = gen_scored[0][2] if gen_scored else {}
        hits = sum(1 for _, _, m in gen_scored if passes_target(m))
        print(f"    [Gen {gen}] best Sharpe={best.get('Sharpe Ratio',0):.2f}"
              f"  Mo={best.get('monthly_roi',0):.2f}%"
              f"  MDD={best.get('Max Drawdown %',0):.1f}%  hits={hits}")

    return all_hits


# ── Main ──────────────────────────────────────────────────────────────────────

def run_tf_search(tf: str, coins: list, args) -> list:
    """Full 3-phase search for a single base timeframe across all coins."""
    risk = dict(risk_per_trade=args.risk_per_trade, leverage=args.leverage)

    print(f"\n{'═'*68}")
    print(f"  TF={tf}  Coins={coins}  N={args.n}  Gens={args.generations}")
    print(f"  HTF hierarchy: {TF_HIERARCHY.get(tf)}")
    print(f"  Target: Sharpe {TARGET['sharpe_min']}–{TARGET['sharpe_max']} | "
          f"MDD≤{TARGET['mdd_max']}% | Monthly {TARGET['monthly_min']}–{TARGET['monthly_max']}%")
    print(f"{'═'*68}\n")

    # Load data for all coins
    data = {}
    for coin in coins:
        try:
            df = load_data(coin, tf, args.date_from, args.date_to)
            if df is not None and len(df) > 200:
                data[coin] = df
                print(f"  Loaded {coin} {tf}: {len(df):,} bars")
        except Exception as e:
            print(f"  [SKIP] {coin} {tf}: {e}")

    if not data:
        print("  [ERROR] No data loaded — skipping TF.")
        return []

    primary_coin = next(iter(data))

    # ── Phase 1: Random ───────────────────────────────────────────────────────
    print(f"\n[Phase 1] Random search ({args.n} candidates across {len(data)} coins)...")
    phase1 = run_phase1_random(data, args.n, tf, risk, seed=args.seed)
    p1_hits = [x for x in phase1 if passes_target(x[2])]
    print(f"  Phase 1 done: {len(phase1)} valid  |  {len(p1_hits)} hit target")

    # ── Phase 2: Presets ──────────────────────────────────────────────────────
    print(f"\n[Phase 2] MTF preset candidates ({len(_make_presets(tf, primary_coin))} presets)...")
    phase2 = run_phase2_presets(data, tf, primary_coin, risk)
    p2_hits = [x for x in phase2 if passes_target(x[2])]
    print(f"  Phase 2 done: {len(p2_hits)} presets hit target")

    # ── Phase 3: Evolution ────────────────────────────────────────────────────
    combined = sorted(phase1 + phase2, key=lambda x: x[0], reverse=True)
    if args.generations > 0 and len(combined) >= 2:
        print(f"\n[Phase 3] Genetic evolution ({args.generations} generations × {args.offspring} offspring)...")
        phase3_hits = run_phase3_evolve(combined, data, tf, risk,
                                        args.generations, args.offspring, args.seed)
        print(f"  Phase 3 done: {len(phase3_hits)} new hits")
    else:
        phase3_hits = []

    # ── Aggregate all hits ────────────────────────────────────────────────────
    all_hits = p1_hits + p2_hits + phase3_hits

    # Deduplicate by (entry, filters_tuple, exit)
    seen   = set()
    unique = []
    for sc, dna, nm in all_hits:
        key = (dna.entry, tuple(sorted(dna.filters)), dna.exit_method)
        if key not in seen:
            seen.add(key)
            unique.append((sc, dna, nm, tf))

    unique.sort(key=lambda x: x[0], reverse=True)
    return unique


def main():
    parser = argparse.ArgumentParser(description='Multi-coin multi-TF strategy forge search')
    parser.add_argument('--coins',        default='all',
                        help=f'Comma-separated coins or "all". Available: {",".join(ALL_COINS)}')
    parser.add_argument('--tf',           default='1h',
                        help='Base timeframe or "all": 5m,15m,1h,4h,1d')
    parser.add_argument('--date_from',    default='2022-01-01')
    parser.add_argument('--date_to',      default='2026-06-01')
    parser.add_argument('--n',            type=int,   default=300,  help='Random population per TF')
    parser.add_argument('--generations',  type=int,   default=8,    help='Evolution generations')
    parser.add_argument('--offspring',    type=int,   default=40,   help='Offspring per generation')
    parser.add_argument('--risk_per_trade', type=float, default=0.05)
    parser.add_argument('--leverage',     type=float, default=5.0)
    parser.add_argument('--seed',         type=int,   default=42)
    parser.add_argument('--top',          type=int,   default=20,   help='Top results to save per TF')
    args = parser.parse_args()

    # Resolve coins
    if args.coins.lower() == 'all':
        coins = ALL_COINS
    else:
        coins = [c.strip().upper() for c in args.coins.split(',')]

    # Resolve TFs
    if args.tf.lower() == 'all':
        tfs = ALL_TFS
    else:
        tfs = [t.strip() for t in args.tf.split(',')]

    print(f"\n{'═'*68}")
    print(f"  Strategy Forge — Multi-Coin Multi-TF Search")
    print(f"  Coins   : {coins}")
    print(f"  TFs     : {tfs}")
    print(f"  N/TF    : {args.n}  |  Generations: {args.generations}")
    print(f"  Risk    : {args.risk_per_trade} per trade  |  Leverage: {args.leverage}x")
    print(f"{'═'*68}")

    all_results = []

    for tf in tfs:
        hits = run_tf_search(tf, coins, args)
        all_results.extend(hits)

    if not all_results:
        print("\n[DONE] No strategies hit the target criteria.")
        return

    # Global ranking
    all_results.sort(key=lambda x: x[0], reverse=True)

    print(f"\n\n{'═'*68}")
    print(f"  GLOBAL TOP RESULTS — {len(all_results)} unique strategies hit target")
    print(f"{'═'*68}\n")
    print(f"  {'#':<3} {'TF':<5} {'Entry':<24} {'Filters':<40} {'Exit':<22} {'Sharpe':>7} {'Mo%':>6} {'MDD%':>6} {'Trades':>7} {'WR%':>6}")
    print(f"  {'-'*3} {'-'*5} {'-'*24} {'-'*40} {'-'*22} {'-'*7} {'-'*6} {'-'*6} {'-'*7} {'-'*6}")

    output = []
    for rank, (sc, dna, nm, tf) in enumerate(all_results[:args.top], 1):
        sh     = nm.get('Sharpe Ratio', 0)
        mo     = nm.get('monthly_roi', 0)
        mdd    = abs(nm.get('Max Drawdown %', 0))
        trades = int(nm.get('Total Trades', 0))
        wr     = nm.get('Win Rate', 0)
        print(f"  {rank:<3} {tf:<5} {dna.entry:<24} {str(dna.filters):<40} {dna.exit_method:<22} "
              f"{sh:>7.2f} {mo:>6.2f} {mdd:>6.1f} {trades:>7} {wr:>6.1f}")

        output.append({
            'rank':        rank,
            'tf':          tf,
            'entry':       dna.entry,
            'filters':     dna.filters,
            'exit':        dna.exit_method,
            'params':      {k: v for k, v in dna.params.items()
                            if not k.startswith('_')},
            'sharpe':      round(sh, 3),
            'monthly_roi': round(mo, 2),
            'mdd':         round(mdd, 2),
            'win_rate':    round(wr, 2),
            'trades':      trades,
            'blend_score': round(sc, 4),
        })

    # Save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts   = datetime.now().strftime('%Y%m%d_%H%M')
    tf_tag = args.tf.replace(',', '-')
    path = os.path.join(RESULTS_DIR, f'multi_forge_{tf_tag}_{ts}.json')
    with open(path, 'w') as f:
        json.dump({
            'run_at':  datetime.now().isoformat(),
            'coins':   coins,
            'tfs':     tfs,
            'n':       args.n,
            'target':  TARGET,
            'results': output,
        }, f, indent=2)
    print(f"\n  Saved {len(output)} results → {path}")


if __name__ == '__main__':
    main()
