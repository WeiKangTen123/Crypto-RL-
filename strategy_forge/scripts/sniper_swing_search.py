"""
sniper_swing_search.py — Targeted search for Sniper-Swing strategies.

Style: LTF (5m/15m) entry precision + HTF (1h/4h) bias filter + forced time-exit.
       NOT classical HFT — this is a "Scalp-to-Swing" hybrid pattern.

Architecture:
  Layer 1 → HTF Bias Filter  : htf_ema_trend / htf_supertrend (resamples 5m→1h or 5m→4h)
  Layer 2 → LTF Entry Signal : precision trigger on 5m or 15m bars
  Layer 3 → Forced Exit      : atr_tp_sl_hold (TP/SL + max_hold_bars)

Holding period targets:
  On 5m  data: 12 bars = 1h  |  48 bars = 4h
  On 15m data:  4 bars = 1h  |  16 bars = 4h

Run examples:
  python strategy_forge/scripts/sniper_swing_search.py --tf 5m --coin BTC --n 300
  python strategy_forge/scripts/sniper_swing_search.py --tf 15m --coin ETH --n 200 --phase2
  python strategy_forge/scripts/sniper_swing_search.py --tf 5m --coin BTC --n 400 --phase2 --evolve --generations 5
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
from strategy_forge.params.ranges import sample_params, DEFAULT_RANGES

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')

# ── Sniper-Swing Signal Universe ─────────────────────────────────────────────
# Entry: precision LTF triggers — fast, reactive to short-term structure
SNIPER_ENTRY_SIGNALS = [
    # Trend reversals (best for 5m/15m precision entries)
    'ema_cross',        'ema_cross',        'ema_cross',    # oversample
    'hma_cross',        'hma_cross',                         # low-lag
    'zlema_cross',
    'supertrend',       'supertrend',
    'parabolic_sar',
    # Structure / order-flow entries (ICT-style)
    'fvg',              'fvg_zone_touch',
    'imbalance_zone',
    'squeeze_breakout',
    # Momentum reversals (mean-revert into HTF trend)
    'stoch_rsi_reversion',
    'williams_r_reversion',
    'bb_reversion',
    'keltner_reversion',
    'wavetrend',
    'vwap_reversion',
    # Volume-driven
    'taker_momentum',
    'cvd_cross',
]

# Filters: must use HTF bias (at least one of the following)
HTF_FILTERS = [
    'htf_ema_trend',
    'htf_supertrend',
]

# Secondary filters: gate noise on same TF
SECONDARY_FILTERS = [
    'adx_trend',
    'wr_not_extreme',
    'rsi_not_extreme',
    'vol_expansion',
    'atr_expansion',
    'obv_trend',
    'hma_slope',
    'psar_trend',
    'taker_confirm',
]

# Exits: must include time-cap (forced sell)
FORCED_EXIT_METHODS = [
    'atr_tp_sl_hold',   # ATR TP/SL + max_hold_bars  ← primary
    'chandelier_tp',    # trailing ATR stop + TP target
    'tight_atr',        # tight SL, moderate TP
    'atr_tp_sl',        # standard ATR TP/SL (no time cap, but fast)
]


def _bars_per_hour(tf: str) -> int:
    """Return number of bars per 1 hour for a given timeframe string."""
    return {'1m': 60, '5m': 12, '15m': 4, '30m': 2, '1h': 1, '4h': 0}.get(tf, 12)


def _htf_bars_for_filter(tf: str, target_htf: str = '1h') -> int:
    """
    Compute the `htf_bars` param so the resampling filter targets a specific HTF.
    e.g. tf=5m, target_htf=4h → 48 bars of 5m = 4h
    """
    mapping = {
        ('5m',  '1h'):  12,
        ('5m',  '4h'):  48,
        ('15m', '1h'):   4,
        ('15m', '4h'):  16,
        ('30m', '1h'):   2,
        ('30m', '4h'):   8,
        ('1h',  '4h'):   4,
    }
    return mapping.get((tf, target_htf), 4)


def _make_sniper_dna(tf: str, seed: int = None, htf_target: str = '4h') -> StrategyDNA:
    """
    Compose one Sniper-Swing DNA:
      - Always includes exactly 1 HTF filter
      - Optionally adds 1 secondary filter
      - Exit is time-capped (atr_tp_sl_hold or similar)
      - max_hold_bars tuned for 1h–4h hold period
    """
    rng = random.Random(seed)

    entry  = rng.choice(SNIPER_ENTRY_SIGNALS)
    htf_f  = rng.choice(HTF_FILTERS)
    sec_f  = rng.choice(SECONDARY_FILTERS) if rng.random() < 0.7 else None
    exit_m = rng.choice(FORCED_EXIT_METHODS)

    filters = [htf_f] + ([sec_f] if sec_f else [])

    # Collect all required param names
    param_names = list(set(
        _ENTRY_PARAMS.get(entry, []) +
        _FILTER_PARAMS.get(htf_f, []) +
        (_FILTER_PARAMS.get(sec_f, []) if sec_f else []) +
        _EXIT_PARAMS.get(exit_m, [])
    ))
    params = sample_params(param_names, seed=seed)

    # ── Force sniper-swing specific overrides ────────────────────────────────
    # 1. HTF target (e.g. 5m bars → 4h = 48 bars)
    params['htf_bars']     = _htf_bars_for_filter(tf, htf_target)
    params['htf_ema_period'] = rng.choice([21, 34, 50, 100, 200])

    # 2. Forced holding period: 1h–4h in base-TF bars
    bph = _bars_per_hour(tf)
    min_hold = bph * 1          # 1h minimum
    max_hold = bph * 4          # 4h maximum
    params['max_hold_bars'] = rng.randint(min_hold, max_hold)

    # 3. TP/SL calibrated for swing (wider TP, tighter SL)
    params['tp_atr_mult'] = round(rng.uniform(2.0, 5.0), 2)
    params['sl_atr_mult'] = round(rng.uniform(0.8, 2.0), 2)
    params['atr_period']  = rng.choice([7, 10, 14])

    # 4. LTF EMA fast/slow — keep narrow for 5m/15m precision
    if 'ema_fast' in params and 'ema_slow' in params:
        params['ema_fast'] = rng.choice([5, 7, 8, 9, 10])
        params['ema_slow'] = rng.choice([18, 20, 21, 25, 34])

    # 5. Supertrend params — tighter for LTF
    if 'st_period' in params:
        params['st_period']     = rng.choice([7, 10, 12, 14])
        params['st_multiplier'] = round(rng.uniform(1.5, 3.5), 2)

    # 6. FVG zone params: if using fvg_zone_touch, set HTF resample correctly
    if entry == 'fvg_zone_touch':
        params['fvg_htf_bars']     = _htf_bars_for_filter(tf, htf_target)
        params['fvg_zone_timeout'] = rng.randint(4, 12)
        params['fvg_cooldown']     = _htf_bars_for_filter(tf, htf_target) * 2
        params['fvg_min_pct']      = round(rng.uniform(0.002, 0.008), 4)

    return StrategyDNA(_placeholder_df(), entry=entry, filters=filters, exit_method=exit_m, params=params)


def _target_score(m: dict, tf: str) -> float:
    """
    Score a strategy by how well it hits the Sniper-Swing targets:
      - Monthly profit: 1.5–5%
      - MDD: < 25%
      - Win rate: 35–60%
      - Trades per week: 2–15 (on LTF this is realistic for short holds)
    """
    try:
        bph      = _bars_per_hour(tf)
        roi      = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
        sharpe   = float(str(m.get('Sharpe Ratio',  '0')) or 0)
        mdd      = abs(float(str(m.get('Max Drawdown %', '100')) or 100))
        wr       = float(str(m.get('Win Rate',       '0')).replace('%', '') or 0)
        trades   = int(m.get('Total Trades', 0) or 0)
        pf       = float(str(m.get('Profit Factor',  '0')) or 0)
        if pf >= 99:
            pf = 2.0

        mdd_penalty  = max(0, mdd - 25) * 0.3
        pf_bonus     = min(pf, 3.0) * 5
        return sharpe * 10 + roi * 0.1 - mdd_penalty + pf_bonus
    except Exception:
        return -999.0


def print_result(rank, score, dna, m, tf):
    bph    = _bars_per_hour(tf)
    try:
        roi     = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
        sharpe  = float(str(m.get('Sharpe Ratio',  '0')) or 0)
        mdd     = abs(float(str(m.get('Max Drawdown %', '?')) or 0))
        wr      = float(str(m.get('Win Rate',       '0')).replace('%', '') or 0)
        trades  = int(m.get('Total Trades', 0) or 0)
        pf      = float(str(m.get('Profit Factor',  '0')) or 0)
        hold    = dna.params.get('max_hold_bars', '?')
        hold_h  = f'{round(hold / bph, 1)}h' if isinstance(hold, (int, float)) else '?'
    except Exception:
        roi = sharpe = mdd = wr = pf = 0; trades = 0; hold_h = '?'

    print(f"  #{rank:>2}  score={score:>8.2f}  ROI={roi:.1f}%  Sharpe={sharpe:.2f}  "
          f"MDD={mdd:.1f}%  WR={wr:.1f}%  Trades={trades}  PF={pf:.2f}")
    print(f"       Hold: {hold_h}  |  {dna.entry} + {dna.filters} → {dna.exit_method}")
    print(f"       params: { {k: v for k, v in dna.params.items() if not k.startswith('_')} }")
    print()


def main():
    parser = argparse.ArgumentParser(description='Sniper-Swing Strategy Search (5m/15m entry, 1h–4h hold)')
    parser.add_argument('--coin',        default='BTC',        help='Coin (BTC, ETH, SOL, ...)')
    parser.add_argument('--tf',          default='5m',         help='Entry timeframe: 5m or 15m')
    parser.add_argument('--htf',         default='4h',         help='Bias timeframe: 1h or 4h')
    parser.add_argument('--date_from',   default='2023-01-01', help='Start date')
    parser.add_argument('--date_to',     default='2026-06-01', help='End date')
    parser.add_argument('--n',           type=int, default=200, help='Phase 1 random candidates')
    parser.add_argument('--top',         type=int, default=10,  help='Top N to display and save')
    parser.add_argument('--min_trades',  type=int, default=30,  help='Minimum trades to qualify')
    parser.add_argument('--score',       default='blend',       help='roi | sharpe | blend')
    parser.add_argument('--phase2',      action='store_true',   help='Run Phase 2 hand-crafted setups')
    parser.add_argument('--evolve',      action='store_true',   help='Run Phase 3 genetic evolution')
    parser.add_argument('--generations', type=int, default=5,   help='Genetic evolution generations')
    parser.add_argument('--seed',        type=int, default=42)
    parser.add_argument('--risk',        type=float, default=0.02, help='risk_per_trade fraction')
    parser.add_argument('--leverage',    type=float, default=5.0)
    args = parser.parse_args()

    RISK = dict(risk_per_trade=args.risk, leverage=args.leverage,
                trading_fee=0.0004, slippage_pct=0.0006)

    bph = _bars_per_hour(args.tf)
    hold_range = f"{bph}–{bph * 4} bars ({1}h–{4}h)"

    print(f"\n{'='*70}")
    print(f"  🎯 Sniper-Swing Search — {args.coin} @ {args.tf}")
    print(f"  HTF Bias: {args.htf}  |  Hold: {hold_range}  |  N: {args.n}")
    print(f"  Score: {args.score}  |  Risk/Trade: {args.risk*100:.1f}%  |  Leverage: {args.leverage}x")
    print(f"{'='*70}\n")

    df = load_data(args.coin, args.tf, args.date_from, args.date_to)
    if df is None or df.empty:
        print('[ERROR] No data loaded. Check coin/tf combination.')
        sys.exit(1)
    print(f"  Loaded {len(df):,} bars  ({df.index[0].date()} → {df.index[-1].date()})\n")

    all_results = []  # (score, dna_dict, metrics, source_label)

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: Random Sniper-Swing Population
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"[Phase 1] Generating {args.n} random Sniper-Swing DNAs...\n")
    rng = random.Random(args.seed)
    population = []
    for i in range(args.n):
        dna = _make_sniper_dna(args.tf, seed=rng.randint(0, 2**31), htf_target=args.htf)
        dna.df = df.copy()
        population.append(dna)

    print(f"  Running backtests ({args.n} strategies)...\n")
    scored_p1 = score_population(population, df, risk=RISK,
                                  score_mode=args.score,
                                  min_trades=args.min_trades,
                                  verbose=True)

    valid_p1 = [(s, dna, m) for s, dna, m in scored_p1 if s > -999]
    print(f"\n  Phase 1 valid: {len(valid_p1)}/{args.n}\n")
    for rank, (s, dna, m) in enumerate(valid_p1[:args.top], 1):
        print_result(rank, s, dna, m, args.tf)
        all_results.append((s, dna.to_dict(), m, 'P1_random'))

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Hand-Crafted Sniper-Swing Compositions
    # ═══════════════════════════════════════════════════════════════════════════
    if args.phase2:
        print(f"\n{'─'*70}")
        print(f"[Phase 2] Hand-crafted Sniper-Swing candidates...\n")

        htf_bars_val = _htf_bars_for_filter(args.tf, args.htf)
        bph = _bars_per_hour(args.tf)

        HAND_CRAFTED = [
            {
                'name': f'SS-A: HMA_cross({args.tf}) + HTF_EMA({args.htf}) + ADX | atr_tp_sl_hold',
                'entry': 'hma_cross',
                'filters': ['htf_ema_trend', 'adx_trend'],
                'exit': 'atr_tp_sl_hold',
                'params': {
                    'ema_fast': 8, 'ema_slow': 21,
                    'htf_bars': htf_bars_val, 'htf_ema_period': 50,
                    'adx_period': 14, 'adx_threshold': 22,
                    'atr_period': 14, 'tp_atr_mult': 3.0, 'sl_atr_mult': 1.5,
                    'max_hold_bars': bph * 3,  # 3h
                },
            },
            {
                'name': f'SS-B: EMA_cross({args.tf}) + HTF_Supertrend({args.htf}) + WR | atr_tp_sl_hold',
                'entry': 'ema_cross',
                'filters': ['htf_supertrend', 'wr_not_extreme'],
                'exit': 'atr_tp_sl_hold',
                'params': {
                    'ema_fast': 9, 'ema_slow': 21,
                    'htf_bars': htf_bars_val, 'st_period': 10, 'st_multiplier': 3.0,
                    'period': 14,
                    'atr_period': 14, 'tp_atr_mult': 3.5, 'sl_atr_mult': 1.5,
                    'max_hold_bars': bph * 2,  # 2h
                },
            },
            {
                'name': f'SS-C: FVG_zone_touch({args.tf}) + HTF_EMA({args.htf}) | chandelier_tp',
                'entry': 'fvg_zone_touch',
                'filters': ['htf_ema_trend'],
                'exit': 'chandelier_tp',
                'params': {
                    'fvg_htf_bars': htf_bars_val, 'fvg_zone_timeout': 8,
                    'fvg_cooldown': htf_bars_val * 2, 'fvg_min_pct': 0.003,
                    'htf_bars': htf_bars_val, 'htf_ema_period': 50,
                    'atr_period': 14, 'atr_multiplier': 2.5, 'tp_atr_mult': 4.0,
                    'max_hold_bars': bph * 4,  # 4h
                },
            },
            {
                'name': f'SS-D: Supertrend({args.tf}) + HTF_EMA({args.htf}) + OBV | atr_tp_sl_hold',
                'entry': 'supertrend',
                'filters': ['htf_ema_trend', 'obv_trend'],
                'exit': 'atr_tp_sl_hold',
                'params': {
                    'st_period': 10, 'st_multiplier': 2.5,
                    'htf_bars': htf_bars_val, 'htf_ema_period': 100,
                    'obv_period': 20,
                    'atr_period': 14, 'tp_atr_mult': 3.0, 'sl_atr_mult': 1.5,
                    'max_hold_bars': bph * 2,
                },
            },
            {
                'name': f'SS-E: StochRSI_rev({args.tf}) + HTF_Supertrend({args.htf}) + ADX | tight_atr',
                'entry': 'stoch_rsi_reversion',
                'filters': ['htf_supertrend', 'adx_trend'],
                'exit': 'tight_atr',
                'params': {
                    'rsi_period': 14, 'smoothing': 3,
                    'rsi_oversold': 20, 'rsi_overbought': 80,
                    'htf_bars': htf_bars_val, 'st_period': 10, 'st_multiplier': 3.0,
                    'adx_period': 14, 'adx_threshold': 20,
                    'atr_period': 14, 'sl_atr_mult': 1.2, 'tp_atr_mult': 4.0,
                    'max_hold_bars': bph * 2,
                },
            },
            {
                'name': f'SS-F: BB_reversion({args.tf}) + HTF_EMA({args.htf}) + vol_expansion | atr_tp_sl_hold',
                'entry': 'bb_reversion',
                'filters': ['htf_ema_trend', 'vol_expansion'],
                'exit': 'atr_tp_sl_hold',
                'params': {
                    'bb_period': 20, 'bb_std': 2.0,
                    'htf_bars': htf_bars_val, 'htf_ema_period': 50,
                    'vol_ma_period': 20, 'vol_multiplier': 1.3,
                    'atr_period': 14, 'tp_atr_mult': 2.5, 'sl_atr_mult': 1.2,
                    'max_hold_bars': bph * 2,
                },
            },
            {
                'name': f'SS-G: WilliamsR_rev({args.tf}) + HTF_Supertrend({args.htf}) | atr_tp_sl_hold',
                'entry': 'williams_r_reversion',
                'filters': ['htf_supertrend'],
                'exit': 'atr_tp_sl_hold',
                'params': {
                    'period': 14,
                    'htf_bars': htf_bars_val, 'st_period': 10, 'st_multiplier': 3.0,
                    'atr_period': 14, 'tp_atr_mult': 3.0, 'sl_atr_mult': 1.5,
                    'max_hold_bars': bph * 3,
                },
            },
            {
                'name': f'SS-H: Taker_momentum({args.tf}) + HTF_EMA({args.htf}) + ATR_expand | chandelier_tp',
                'entry': 'taker_momentum',
                'filters': ['htf_ema_trend', 'atr_expansion'],
                'exit': 'chandelier_tp',
                'params': {
                    'intensity_period': 20, 'taker_threshold': 0.6,
                    'htf_bars': htf_bars_val, 'htf_ema_period': 50,
                    'atr_period': 14, 'vol_ma_period': 50,
                    'atr_multiplier': 3.0, 'tp_atr_mult': 4.0,
                    'max_hold_bars': bph * 4,
                },
            },
        ]

        p2_results = []
        for c in HAND_CRAFTED:
            dna = StrategyDNA(df.copy(), c['entry'], c['filters'], c['exit'], c['params'])
            s, m = score_dna(dna, df, risk=RISK, score_mode=args.score, min_trades=args.min_trades)
            p2_results.append((s, dna, m, c['name']))
            status = '✓' if s > -999 else '✗'
            try:
                roi = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
                sharpe = float(str(m.get('Sharpe Ratio', '0')) or 0)
                mdd = abs(float(str(m.get('Max Drawdown %', '0')) or 0))
                wr = float(str(m.get('Win Rate', '0')).replace('%', '') or 0)
                trades = int(m.get('Total Trades', 0) or 0)
            except Exception:
                roi = sharpe = mdd = wr = 0; trades = 0
            print(f"  {status} {c['name']}")
            print(f"    score={s:.2f}  ROI={roi:.1f}%  Sharpe={sharpe:.2f}  MDD={mdd:.1f}%  "
                  f"WR={wr:.1f}%  Trades={trades}\n")

        p2_valid = [(s, dna, m, name) for s, dna, m, name in p2_results if s > -999]
        p2_valid.sort(key=lambda x: -x[0])

        print(f"\n  Phase 2 Top Results:\n")
        for rank, (s, dna, m, name) in enumerate(p2_valid, 1):
            print_result(rank, s, dna, m, args.tf)
            all_results.append((s, dna.to_dict(), m, f'P2_{name[:20]}'))

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: Genetic Evolution on top Phase-1 survivors
    # ═══════════════════════════════════════════════════════════════════════════
    if args.evolve and valid_p1:
        print(f"\n{'─'*70}")
        print(f"[Phase 3] Genetic Evolution — {args.generations} generations\n")

        scored_pairs = [(s, dna) for s, dna, _ in scored_p1]
        current_scored = scored_p1

        hall_of_fame = []

        for gen in range(1, args.generations + 1):
            valid_gen = [(s, dna, m) for s, dna, m in current_scored if s > -999]
            hall_of_fame.extend([(s, dna.to_dict(), m) for s, dna, m in valid_gen])
            hall_of_fame.sort(key=lambda x: -x[0])
            hall_of_fame = hall_of_fame[:20]

            scored_pairs = [(s, dna) for s, dna, _ in current_scored]
            new_pop = genetic_evolve(
                scored_pairs, df,
                n_survivors=10,
                n_offspring=25,
                mutation_rate=0.25,
                seed=args.seed + gen,
            )

            # Force max_hold_bars range after crossover/mutation
            for dna in new_pop:
                bph = _bars_per_hour(args.tf)
                if 'max_hold_bars' not in dna.params or \
                   not (bph <= dna.params.get('max_hold_bars', 0) <= bph * 4):
                    dna.params['max_hold_bars'] = random.randint(bph, bph * 4)

            print(f"  [Gen {gen}] Scoring {len(new_pop)} strategies...\n")
            current_scored = score_population(new_pop, df, risk=RISK,
                                              score_mode=args.score,
                                              min_trades=args.min_trades,
                                              verbose=True)

        print(f"\n  Hall of Fame — Top {min(args.top, len(hall_of_fame))}:\n")
        for rank, (s, dna_d, m) in enumerate(hall_of_fame[:args.top], 1):
            dna_tmp = StrategyDNA(df, dna_d['entry'], dna_d['filters'],
                                   dna_d['exit_method'], dna_d['params'])
            print_result(rank, s, dna_tmp, m, args.tf)
            all_results.append((s, dna_d, m, f'P3_evolved'))

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL RANKING & SAVE
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  🏆 FINAL TOP {args.top} SNIPER-SWING STRATEGIES\n")

    all_results.sort(key=lambda x: -x[0])
    top_results = all_results[:args.top]

    for rank, (s, dna_d, m, src) in enumerate(top_results, 1):
        dna_tmp = StrategyDNA(df, dna_d['entry'], dna_d['filters'],
                               dna_d['exit_method'], dna_d['params'])
        print_result(rank, s, dna_tmp, m, args.tf)

    # Save to JSON
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(RESULTS_DIR,
        f'sniper_swing_{args.coin}_{args.tf}_{args.htf}_{ts}.json')

    output = {
        'run_at':      datetime.now().isoformat(),
        'style':       'sniper_swing',
        'coin':        args.coin,
        'entry_tf':    args.tf,
        'bias_tf':     args.htf,
        'date_from':   args.date_from,
        'date_to':     args.date_to,
        'n_tested':    args.n,
        'score_mode':  args.score,
        'risk':        RISK,
        'top_results': [
            {
                'rank':        rank,
                'score':       float(s),
                'source':      src,
                'entry':       d['entry'],
                'filters':     d['filters'],
                'exit_method': d['exit_method'],
                'params':      d['params'],
                'hold_hours':  round(d['params'].get('max_hold_bars', 0)
                                     / _bars_per_hour(args.tf), 1),
                'metrics': {
                    'total_return':  m.get('Total Return'),
                    'sharpe':        m.get('Sharpe Ratio'),
                    'max_drawdown':  m.get('Max Drawdown %'),
                    'win_rate':      m.get('Win Rate'),
                    'total_trades':  m.get('Total Trades'),
                    'profit_factor': m.get('Profit Factor'),
                },
            }
            for rank, (s, d, m, src) in enumerate(top_results, 1)
        ],
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved → {out_path}")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
