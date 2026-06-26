"""
hft_search.py — targeted search for HFT / scalp strategies.

Style: 5m or 15m base TF, 1-10 bar hold (5-50 min), 20-100 trades/week.
Uses tight SL (0.3-0.8 ATR), moderate TP (1.5-4.0 ATR), and fast reversal entries.

Fee note: at 5× leverage, round-trip fee ≈ 0.4% equity per trade.
          Need avg PF ≥ 1.5 and WR ≥ 45% to survive 50 trades/week.

Usage
-----
python strategy_forge/scripts/hft_search.py --coin BTC --tf 5m --n 300
python strategy_forge/scripts/hft_search.py --coin ETH --tf 15m --n 200 --phase2
python strategy_forge/scripts/hft_search.py --coin BTC --tf 5m --n 400 --phase2 --evolve --generations 5
"""
import os
import sys
import json
import random
import argparse
from datetime import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest import load_data
from strategy_forge.composer.dna import StrategyDNA
from strategy_forge.composer.random_compose import _ENTRY_PARAMS, _FILTER_PARAMS, _EXIT_PARAMS, _placeholder_df
from strategy_forge.composer.genetic import evolve as genetic_evolve
from strategy_forge.runner.backtest_runner import score_dna, score_population
from strategy_forge.params.ranges import sample_params

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')

# ── HFT Signal Universe ───────────────────────────────────────────────────────
# Fast reversal signals best suited for 5m/15m scalping
HFT_ENTRY_SIGNALS = [
    'stoch_rsi_reversion', 'stoch_rsi_reversion',  # oversample — best for scalp
    'williams_r_reversion', 'williams_r_reversion',
    'candle_engulfing',    'candle_engulfing',
    'candle_pin_bar',      'candle_pin_bar',
    'bb_reversion',        'bb_reversion',
    'wavetrend',
    'keltner_reversion',
    'vwap_reversion',
    'imbalance_zone',
    'fisher',
    'order_block',
]

# Noise filters — gate entries in choppy/low-volume conditions
HFT_FILTERS = [
    'adx_trend',
    'vol_expansion',
    'atr_expansion',
    'rsi_not_extreme',
    'wr_not_extreme',
    'taker_confirm',
    'hma_slope',
]

# Exits: fast cutoff, let winners trail briefly
HFT_EXIT_METHODS = [
    'breakeven_trail',   # cut losers fast, trail winners ← primary
    'tight_atr',         # tight SL, moderate TP
    'rsi_exit',          # exit on RSI midline cross
    'max_hold',          # pure time stop (for pure reversal plays)
    'atr_tp_sl_hold',    # ATR TP/SL + forced time cap
    'pct_tp_sl',         # fixed % TP/SL (clean for scalp)
]


def _bars_per_hour(tf: str) -> int:
    return {'1m': 60, '5m': 12, '15m': 4, '30m': 2, '1h': 1, '4h': 0}.get(tf, 12)


def _make_hft_dna(tf: str, seed: int = None) -> StrategyDNA:
    """
    Compose one HFT DNA:
      - Fast reversal entry
      - 0-1 noise filter (fewer filters = more signals)
      - Tight exit (breakeven_trail or tight_atr preferred)
      - max_hold_bars: 1-10 base-TF bars
      - Tight SL: 0.3-0.8 ATR
      - Moderate TP: 1.5-4.0 ATR
    """
    rng    = random.Random(seed)
    entry  = rng.choice(HFT_ENTRY_SIGNALS)
    exit_m = rng.choice(HFT_EXIT_METHODS)

    # 0 or 1 filter for HFT — fewer filters = higher signal frequency
    n_filters = rng.randint(0, 1)
    filters   = rng.sample(HFT_FILTERS, k=n_filters)

    param_names = list(set(
        _ENTRY_PARAMS.get(entry, []) +
        sum([_FILTER_PARAMS.get(f, []) for f in filters], []) +
        _EXIT_PARAMS.get(exit_m, [])
    ))
    params = sample_params(param_names, seed=seed)

    bph = _bars_per_hour(tf)

    # ── HFT-specific param overrides ─────────────────────────────────────────
    # 1. Time stop: 1-10 bars (5-50 min on 5m)
    params['max_hold_bars'] = rng.randint(max(1, bph // 4), max(bph, 10))

    # 2. Tight SL, moderate TP (needs good R:R to beat fees)
    params['sl_atr_mult']   = round(rng.uniform(0.3, 0.8), 2)
    params['tp_atr_mult']   = round(rng.uniform(1.5, 4.0), 2)
    params['atr_period']    = rng.choice([5, 7, 10, 14])

    # 3. Breakeven trigger: 0.3-0.6 ATR (trigger quickly)
    params['be_trigger_mult'] = round(rng.uniform(0.3, 0.6), 2)
    params['atr_multiplier']  = round(rng.uniform(1.0, 2.0), 2)

    # 4. Fast RSI for rsi_exit
    if entry in ('stoch_rsi_reversion',):
        params['rsi_period'] = rng.choice([5, 7, 9, 14])
        params['smoothing']  = rng.choice([2, 3])
    elif 'rsi_period' in params:
        params['rsi_period'] = rng.choice([5, 7, 9, 14])

    # 5. BB/Keltner — tighter bands for scalp
    if 'bb_period' in params:
        params['bb_period'] = rng.choice([10, 14, 20])
        params['bb_std']    = round(rng.uniform(1.5, 2.5), 1)

    # 6. WaveTrend — faster oscillation
    if 'wt_n1' in params:
        params['wt_n1'] = rng.choice([5, 7, 8, 10])
        params['wt_n2'] = rng.choice([15, 21, 25])
        if params['wt_n1'] >= params['wt_n2']:
            params['wt_n1'] = max(3, params['wt_n2'] - 5)

    return StrategyDNA(_placeholder_df(), entry=entry, filters=filters,
                       exit_method=exit_m, params=params)


def _hft_score(m: dict) -> float:
    """
    Score a candidate by HFT-specific targets:
      - High Sharpe (signal quality given fee drag)
      - Frequency bonus: 20-80 trades/week
      - MDD < 30%
      - PF ≥ 1.3 (needed to survive fees)
    """
    try:
        sharpe  = float(str(m.get('Sharpe Ratio', '0')) or 0)
        roi     = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
        mdd     = abs(float(str(m.get('Max Drawdown %', '100')) or 100))
        pf      = float(str(m.get('Profit Factor', '0')) or 0)
        if pf >= 99: pf = 2.0
        tpw     = float(m.get('trades_per_week', 0) or 0)

        if mdd > 50:
            return -999.0

        freq_bonus = 0.0
        if 20 <= tpw <= 100:
            freq_bonus = 3.0
        elif 10 <= tpw < 20:
            freq_bonus = 1.5

        mdd_penalty = max(0, mdd - 30) * 0.4
        pf_bonus    = min(pf, 3.0) * 4
        roi_log     = min(roi * 0.05, 5.0)

        return sharpe * 10 + roi_log + freq_bonus + pf_bonus - mdd_penalty
    except Exception:
        return -999.0


def print_result(rank, score, dna, m, tf):
    bph = _bars_per_hour(tf)
    try:
        roi    = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
        sharpe = float(str(m.get('Sharpe Ratio', '0')) or 0)
        mdd    = abs(float(str(m.get('Max Drawdown %', '0')) or 0))
        wr     = float(str(m.get('Win Rate', '0')).replace('%', '') or 0)
        trades = int(m.get('Total Trades', 0) or 0)
        pf     = float(str(m.get('Profit Factor', '0')) or 0)
        tpw    = float(m.get('trades_per_week', 0) or 0)
        hold   = dna.params.get('max_hold_bars', '?')
        hold_m = f'{round(hold / bph * 60, 0):.0f}min' if isinstance(hold, (int, float)) and bph > 0 else '?'
        style  = m.get('style', '')
    except Exception:
        roi = sharpe = mdd = wr = pf = tpw = 0; trades = 0; hold_m = '?'; style = ''

    print(f"  #{rank:>2}  score={score:>8.2f}  ROI={roi:.1f}%  Sharpe={sharpe:.2f}  "
          f"MDD={mdd:.1f}%  WR={wr:.1f}%  PF={pf:.2f}")
    print(f"       Hold: {hold_m}  |  {tpw:.1f}/wk  |  [{style}]")
    print(f"       {dna.entry} + {dna.filters} → {dna.exit_method}")
    print(f"       params: { {k: v for k, v in dna.params.items() if not k.startswith('_')} }")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='HFT / Scalp Strategy Search (5m/15m, 1-10 bar hold, 20-100 trades/wk)')
    parser.add_argument('--coin',        default='BTC',        help='Coin (BTC, ETH, SOL, ...)')
    parser.add_argument('--tf',          default='5m',         help='Entry timeframe: 5m or 15m')
    parser.add_argument('--date_from',   default='2023-01-01', help='Start date')
    parser.add_argument('--date_to',     default='2026-06-01', help='End date')
    parser.add_argument('--n',           type=int, default=300, help='Phase 1 random candidates')
    parser.add_argument('--top',         type=int, default=10,  help='Top N to display and save')
    parser.add_argument('--min_trades',  type=int, default=50,  help='Minimum trades to qualify')
    parser.add_argument('--score',       default='blend',       help='roi | sharpe | blend')
    parser.add_argument('--phase2',      action='store_true',   help='Run Phase 2 hand-crafted setups')
    parser.add_argument('--evolve',      action='store_true',   help='Run Phase 3 genetic evolution')
    parser.add_argument('--generations', type=int, default=5,   help='Genetic evolution generations')
    parser.add_argument('--seed',        type=int, default=42)
    parser.add_argument('--risk',        type=float, default=0.005, help='risk_per_trade fraction')
    parser.add_argument('--leverage',    type=float, default=3.0,   help='Leverage (lower for HFT)')
    args = parser.parse_args()

    RISK = dict(risk_per_trade=args.risk, leverage=args.leverage,
                trading_fee=0.0004, slippage_pct=0.0006)

    bph = _bars_per_hour(args.tf)
    print(f"\n{'='*70}")
    print(f"  HFT Scalp Search — {args.coin} @ {args.tf}")
    print(f"  Hold: 1-10 bars ({1 if bph == 0 else round(1/bph*60,0):.0f}-"
          f"{round(10/bph*60,0):.0f}min)  |  Target: 20-100 trades/wk")
    print(f"  Score: {args.score}  |  Risk/Trade: {args.risk*100:.2f}%  |  Leverage: {args.leverage}x")
    print(f"  Fee drag: ~{args.risk * args.leverage * 0.0008 * 100:.3f}% equity/trade round-trip")
    print(f"{'='*70}\n")

    df = load_data(args.coin, args.tf, args.date_from, args.date_to)
    if df is None or df.empty:
        print('[ERROR] No data loaded. Check coin/tf combination.')
        sys.exit(1)
    print(f"  Loaded {len(df):,} bars  ({df.index[0].date()} → {df.index[-1].date()})\n")

    all_results = []

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: Random HFT Population
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"[Phase 1] Generating {args.n} random HFT DNAs...\n")
    rng = random.Random(args.seed)
    population = []
    for i in range(args.n):
        dna = _make_hft_dna(args.tf, seed=rng.randint(0, 2**31))
        dna.df = df.copy()
        population.append(dna)

    print(f"  Running backtests ({args.n} strategies)...\n")
    scored_p1 = score_population(population, df, risk=RISK,
                                 score_mode=args.score,
                                 min_trades=args.min_trades,
                                 verbose=True)

    valid_p1 = [(s, dna, m) for s, dna, m in scored_p1 if s > -999]
    # Re-rank by HFT-specific scoring
    valid_p1_hft = sorted(valid_p1, key=lambda x: _hft_score(x[2]), reverse=True)

    print(f"\n  Phase 1 valid: {len(valid_p1)}/{args.n}\n")
    for rank, (s, dna, m) in enumerate(valid_p1_hft[:args.top], 1):
        hs = _hft_score(m)
        print_result(rank, hs, dna, m, args.tf)
        all_results.append((hs, dna.to_dict(), m, 'P1_random'))

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Hand-Crafted HFT Setups
    # ═══════════════════════════════════════════════════════════════════════════
    if args.phase2:
        print(f"\n{'─'*70}")
        print(f"[Phase 2] Hand-crafted HFT candidates...\n")

        HAND_CRAFTED = [
            {
                'name': f'HFT-A: StochRSI({args.tf}) + ADX | breakeven_trail',
                'entry': 'stoch_rsi_reversion',
                'filters': ['adx_trend'],
                'exit': 'breakeven_trail',
                'params': {
                    'rsi_period': 9, 'smoothing': 3,
                    'rsi_oversold': 20, 'rsi_overbought': 80,
                    'adx_period': 14, 'adx_threshold': 20,
                    'atr_period': 7, 'sl_atr_mult': 0.5,
                    'be_trigger_mult': 0.4, 'atr_multiplier': 1.5,
                    'max_hold_bars': bph * 1,
                },
            },
            {
                'name': f'HFT-B: WilliamsR({args.tf}) + vol_expansion | tight_atr',
                'entry': 'williams_r_reversion',
                'filters': ['vol_expansion'],
                'exit': 'tight_atr',
                'params': {
                    'period': 14,
                    'vol_ma_period': 20, 'vol_multiplier': 1.5,
                    'atr_period': 7, 'sl_atr_mult': 0.5, 'tp_atr_mult': 2.0,
                    'max_hold_bars': max(1, bph // 2),
                },
            },
            {
                'name': f'HFT-C: CandleEngulfing({args.tf}) + atr_expansion | breakeven_trail',
                'entry': 'candle_engulfing',
                'filters': ['atr_expansion'],
                'exit': 'breakeven_trail',
                'params': {
                    'vol_ma_period': 20,
                    'atr_period': 7, 'sl_atr_mult': 0.4,
                    'be_trigger_mult': 0.3, 'atr_multiplier': 1.5,
                    'max_hold_bars': max(1, bph // 2),
                },
            },
            {
                'name': f'HFT-D: BB_reversion({args.tf}) + ADX | rsi_exit',
                'entry': 'bb_reversion',
                'filters': ['adx_trend'],
                'exit': 'rsi_exit',
                'params': {
                    'bb_period': 14, 'bb_std': 2.0,
                    'adx_period': 14, 'adx_threshold': 18,
                    'rsi_period': 9, 'rsi_threshold': 50,
                    'atr_period': 7, 'sl_atr_mult': 0.6, 'tp_atr_mult': 2.0,
                    'max_hold_bars': bph * 1,
                },
            },
            {
                'name': f'HFT-E: CandlePinBar({args.tf}) + vol_expansion | tight_atr',
                'entry': 'candle_pin_bar',
                'filters': ['vol_expansion'],
                'exit': 'tight_atr',
                'params': {
                    'vol_ma_period': 20, 'vol_multiplier': 1.3,
                    'atr_period': 7, 'sl_atr_mult': 0.5, 'tp_atr_mult': 2.5,
                    'max_hold_bars': max(1, bph // 2),
                },
            },
            {
                'name': f'HFT-F: WaveTrend({args.tf}) + rsi_not_extreme | breakeven_trail',
                'entry': 'wavetrend',
                'filters': ['rsi_not_extreme'],
                'exit': 'breakeven_trail',
                'params': {
                    'wt_n1': 7, 'wt_n2': 21,
                    'wt_oversold': -60, 'wt_overbought': 60,
                    'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70,
                    'atr_period': 7, 'sl_atr_mult': 0.5,
                    'be_trigger_mult': 0.4, 'atr_multiplier': 1.5,
                    'max_hold_bars': bph * 1,
                },
            },
            {
                'name': f'HFT-G: VWAP_reversion({args.tf}) + taker_confirm | tight_atr',
                'entry': 'vwap_reversion',
                'filters': ['taker_confirm'],
                'exit': 'tight_atr',
                'params': {
                    'vwap_period': 20, 'vwap_std_mult': 1.5,
                    'intensity_period': 20,
                    'atr_period': 7, 'sl_atr_mult': 0.5, 'tp_atr_mult': 2.0,
                    'max_hold_bars': max(1, bph // 2),
                },
            },
            {
                'name': f'HFT-H: OrderBlock({args.tf}) + atr_expansion | breakeven_trail',
                'entry': 'order_block',
                'filters': ['atr_expansion'],
                'exit': 'breakeven_trail',
                'params': {
                    'atr_period': 7, 'atr_multiplier': 2.0, 'lookback': 3,
                    'vol_ma_period': 20,
                    'sl_atr_mult': 0.5,
                    'be_trigger_mult': 0.4, 'atr_multiplier': 1.5,
                    'max_hold_bars': max(1, bph // 2),
                },
            },
        ]

        for c in HAND_CRAFTED:
            dna = StrategyDNA(df.copy(), c['entry'], c['filters'], c['exit'], c['params'])
            s, m = score_dna(dna, df, risk=RISK, score_mode=args.score,
                             min_trades=args.min_trades)
            hs = _hft_score(m)
            status = '✓' if s > -999 else '✗'
            try:
                roi    = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
                sharpe = float(str(m.get('Sharpe Ratio', '0')) or 0)
                mdd    = abs(float(str(m.get('Max Drawdown %', '0')) or 0))
                wr     = float(str(m.get('Win Rate', '0')).replace('%', '') or 0)
                trades = int(m.get('Total Trades', 0) or 0)
                tpw    = float(m.get('trades_per_week', 0) or 0)
                style  = m.get('style', '')
            except Exception:
                roi = sharpe = mdd = wr = tpw = 0; trades = 0; style = ''
            print(f"  {status} {c['name']}")
            print(f"    hft_score={hs:.2f}  score={s:.2f}  ROI={roi:.1f}%  Sharpe={sharpe:.2f}"
                  f"  MDD={mdd:.1f}%  WR={wr:.1f}%  Trades={trades}  {tpw:.1f}/wk  [{style}]\n")
            if s > -999:
                all_results.append((hs, dna.to_dict(), m, f'P2_{c["name"][:20]}'))

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: Genetic Evolution on top Phase-1 survivors
    # ═══════════════════════════════════════════════════════════════════════════
    if args.evolve and valid_p1:
        print(f"\n{'─'*70}")
        print(f"[Phase 3] Genetic Evolution — {args.generations} generations\n")

        current_scored = scored_p1
        hall_of_fame   = []

        for gen in range(1, args.generations + 1):
            valid_gen = [(s, dna, m) for s, dna, m in current_scored if s > -999]
            hall_of_fame.extend([(hs, dna.to_dict(), m)
                                 for s, dna, m in valid_gen
                                 for hs in [_hft_score(m)] if hs > -999])
            hall_of_fame.sort(key=lambda x: -x[0])
            hall_of_fame = hall_of_fame[:20]

            scored_pairs  = [(s, dna) for s, dna, _ in current_scored]
            new_pop = genetic_evolve(scored_pairs, df,
                                     n_survivors=10, n_offspring=25,
                                     mutation_rate=0.25, seed=args.seed + gen)

            # Re-enforce HFT hold constraint after mutation
            for dna in new_pop:
                dna.params['max_hold_bars'] = random.randint(
                    max(1, bph // 4), max(bph, 10))
                dna.params['sl_atr_mult']   = round(random.uniform(0.3, 0.8), 2)
                dna.params['tp_atr_mult']   = round(random.uniform(1.5, 4.0), 2)

            print(f"  [Gen {gen}] Scoring {len(new_pop)} strategies...\n")
            current_scored = score_population(new_pop, df, risk=RISK,
                                              score_mode=args.score,
                                              min_trades=args.min_trades,
                                              verbose=True)

        print(f"\n  Hall of Fame — Top {min(args.top, len(hall_of_fame))}:\n")
        for rank, (hs, dna_d, m) in enumerate(hall_of_fame[:args.top], 1):
            dna_tmp = StrategyDNA(df, dna_d['entry'], dna_d['filters'],
                                  dna_d['exit_method'], dna_d['params'])
            print_result(rank, hs, dna_tmp, m, args.tf)
            all_results.append((hs, dna_d, m, 'P3_evolved'))

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL RANKING & SAVE
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  HFT TOP {args.top} (scored by frequency-weighted HFT score)\n")

    all_results.sort(key=lambda x: -x[0])
    top_results = all_results[:args.top]

    for rank, (hs, dna_d, m, src) in enumerate(top_results, 1):
        dna_tmp = StrategyDNA(df, dna_d['entry'], dna_d['filters'],
                              dna_d['exit_method'], dna_d['params'])
        print_result(rank, hs, dna_tmp, m, args.tf)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(RESULTS_DIR, f'hft_search_{args.coin}_{args.tf}_{ts}.json')

    output = {
        'run_at':      datetime.now().isoformat(),
        'style':       'hft',
        'coin':        args.coin,
        'entry_tf':    args.tf,
        'date_from':   args.date_from,
        'date_to':     args.date_to,
        'n_tested':    args.n,
        'score_mode':  args.score,
        'risk':        RISK,
        'top_results': [
            {
                'rank':          rank,
                'hft_score':     float(hs),
                'source':        src,
                'entry':         d['entry'],
                'filters':       d['filters'],
                'exit_method':   d['exit_method'],
                'params':        d['params'],
                'hold_min':      round(d['params'].get('max_hold_bars', 0)
                                       / max(_bars_per_hour(args.tf), 1) * 60, 1),
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
            for rank, (hs, d, m, src) in enumerate(top_results, 1)
        ],
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved → {out_path}")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
