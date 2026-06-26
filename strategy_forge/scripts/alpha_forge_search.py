"""
alpha_forge_search.py — Targeted alpha search using the best-validated signal combos.

Playstyle library tested:
  A. trailing_tp      — profit ratchet (activate → trail behind peak)
  B. psar_trail       — PSAR trailing stop (natural tightening)
  C. vol_adaptive_sl  — volatility-adaptive stop loss width
  D. funding_rate_mr  — funding rate mean reversion entry (ETH/BTC 4h)
  E. zscore_ema       — z-score of price vs EMA (mean reversion)
  F. zscore_htf       — HTF z-score driven LTF entry

Core insight from Strategy #134 tuning: quad-filter (htf_ema_trend + atr_expansion
+ obv_trend + adx_trend) dramatically improves signal quality. This script applies
that pattern systematically with the new exits.

Usage
-----
python strategy_forge/scripts/alpha_forge_search.py --coin ETH --tf 5m --n 200
python strategy_forge/scripts/alpha_forge_search.py --coin BTC --tf 15m --n 150 --top 10
python strategy_forge/scripts/alpha_forge_search.py --coin ETH --tf 4h --n 100 --mode funding
"""
import os
import sys
import json
import argparse
import random
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from strategy_backtest.run_backtest import load_data
from strategy_forge.composer.dna import StrategyDNA
from strategy_forge.runner.backtest_runner import score_dna

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')
REPORT_DIR  = os.path.join(ROOT, 'phase_6_agent_monitor', 'alpha_forge_v2', 'dev_report')

# ── Signal libraries ──────────────────────────────────────────────────────────

# Entry signals proven effective in research
TREND_ENTRIES = ['supertrend', 'ema_cross', 'hma_cross', 'zlema_cross']
REVERSION_ENTRIES = ['zscore_ema', 'zscore_htf', 'zscore_reversion',
                     'stoch_rsi_reversion', 'williams_r_reversion', 'vwap_reversion']
STRUCTURE_ENTRIES = ['fvg_zone_touch', 'order_block', 'imbalance_zone', 'taker_momentum']
FUNDING_ENTRIES   = ['funding_rate_mr']

# New playstyle exits (A/B/C) + proven exits
NEW_EXITS = ['trailing_tp', 'psar_trail', 'vol_adaptive_sl']
PROVEN_EXITS = ['supertrend_trail', 'atr_tp_sl_hold', 'breakeven_trail', 'chandelier_tp']
ALL_EXITS = NEW_EXITS + PROVEN_EXITS

# Quad-filter combo proven in #134 tuning
QUAD_FILTERS   = ['htf_ema_trend', 'atr_expansion', 'obv_trend', 'adx_trend']
TRIPLE_FILTERS = ['htf_ema_trend', 'atr_expansion', 'obv_trend']
DOUBLE_FILTERS = ['htf_ema_trend', 'atr_expansion']

# ── Candidate presets ─────────────────────────────────────────────────────────

def _make_preset_candidates(tf: str, coin: str) -> list:
    """Hand-crafted candidates based on research insights."""
    htf_bars = {'5m': 72, '15m': 24, '1h': 6, '4h': 2}.get(tf, 48)
    return [
        # A1: Supertrend + trailing_tp (trailing profit ratchet)
        {'name': 'ST_trailing_tp',
         'entry': 'supertrend', 'filters': QUAD_FILTERS, 'exit': 'trailing_tp',
         'params': {'st_period': 27, 'st_multiplier': 2.5, 'htf_bars': htf_bars,
                    'htf_ema_period': 50, 'atr_period': 14, 'vol_ma_period': 50,
                    'obv_period': 20, 'adx_period': 14, 'adx_threshold': 31,
                    'sl_atr_mult': 2.0, 'tp_activation_mult': 1.5, 'tp_trail_mult': 0.8,
                    'direction': 'long_only', 'coin': coin}},

        # A2: Supertrend + psar_trail (PSAR dynamic stop)
        {'name': 'ST_psar_trail',
         'entry': 'supertrend', 'filters': QUAD_FILTERS, 'exit': 'psar_trail',
         'params': {'st_period': 27, 'st_multiplier': 2.5, 'htf_bars': htf_bars,
                    'htf_ema_period': 50, 'atr_period': 14, 'vol_ma_period': 50,
                    'obv_period': 20, 'adx_period': 14, 'adx_threshold': 31,
                    'psar_acceleration': 0.02, 'psar_maximum': 0.2,
                    'sl_atr_mult': 2.0, 'tp_atr_mult': 5.0,
                    'direction': 'long_only', 'coin': coin}},

        # A3: Supertrend + vol_adaptive_sl (regime-aware stop)
        {'name': 'ST_vol_adaptive',
         'entry': 'supertrend', 'filters': QUAD_FILTERS, 'exit': 'vol_adaptive_sl',
         'params': {'st_period': 27, 'st_multiplier': 2.5, 'htf_bars': htf_bars,
                    'htf_ema_period': 50, 'atr_period': 14, 'vol_ma_period': 50,
                    'obv_period': 20, 'adx_period': 14, 'adx_threshold': 31,
                    'sl_atr_mult': 2.0, 'tp_atr_mult': 4.0,
                    'direction': 'long_only', 'coin': coin}},

        # B: Funding rate mean reversion (4h TF)
        {'name': 'FR_mr_chandelier',
         'entry': 'funding_rate_mr', 'filters': ['adx_trend', 'atr_expansion'], 'exit': 'chandelier_tp',
         'params': {'fr_long_thresh': -0.0001, 'fr_short_thresh': 0.0003,
                    'adx_period': 14, 'adx_threshold': 20, 'atr_period': 14,
                    'vol_ma_period': 50, 'atr_multiplier': 2.5, 'tp_atr_mult': 5.0,
                    'coin': coin}},

        # C1: Z-score vs EMA mean reversion + triple filter
        {'name': 'ZSEMA_trail',
         'entry': 'zscore_ema', 'filters': TRIPLE_FILTERS, 'exit': 'trailing_tp',
         'params': {'ema_trend': 50, 'zscore_period': 20, 'zscore_threshold': 2.0,
                    'htf_bars': htf_bars, 'htf_ema_period': 50, 'atr_period': 14,
                    'vol_ma_period': 50, 'obv_period': 20,
                    'sl_atr_mult': 1.5, 'tp_activation_mult': 1.0, 'tp_trail_mult': 0.6,
                    'coin': coin}},

        # C2: HTF z-score + LTF entry + vol_adaptive_sl
        {'name': 'ZSHTF_vol_adaptive',
         'entry': 'zscore_htf', 'filters': DOUBLE_FILTERS, 'exit': 'vol_adaptive_sl',
         'params': {'htf_bars': htf_bars, 'zscore_period': 20, 'zscore_threshold': 1.8,
                    'htf_ema_period': 50, 'atr_period': 14, 'vol_ma_period': 50,
                    'sl_atr_mult': 2.0, 'tp_atr_mult': 4.0,
                    'coin': coin}},

        # D: Taker momentum + trailing_tp (HFT momentum capture)
        {'name': 'TAKER_trailing_tp',
         'entry': 'taker_momentum', 'filters': ['htf_ema_trend', 'adx_trend', 'obv_trend'],
         'exit': 'trailing_tp',
         'params': {'intensity_period': 14, 'taker_threshold': 0.6, 'htf_bars': htf_bars,
                    'htf_ema_period': 50, 'adx_period': 14, 'adx_threshold': 25,
                    'obv_period': 20, 'atr_period': 14,
                    'sl_atr_mult': 1.5, 'tp_activation_mult': 1.0, 'tp_trail_mult': 0.7,
                    'coin': coin}},

        # E: EMA cross + PSAR trail (trend-following with natural stop)
        {'name': 'EMA_psar_trail',
         'entry': 'ema_cross', 'filters': ['htf_ema_trend', 'adx_trend', 'atr_expansion'],
         'exit': 'psar_trail',
         'params': {'ema_fast': 8, 'ema_slow': 21, 'htf_bars': htf_bars,
                    'htf_ema_period': 50, 'adx_period': 14, 'adx_threshold': 25,
                    'atr_period': 14, 'vol_ma_period': 50,
                    'psar_acceleration': 0.02, 'psar_maximum': 0.2,
                    'sl_atr_mult': 2.0, 'tp_atr_mult': 5.0,
                    'coin': coin}},
    ]


def _make_random_candidate(tf: str, coin: str, rng: random.Random) -> dict:
    """Generate a random candidate from the new signal pool."""
    all_entries = TREND_ENTRIES + REVERSION_ENTRIES + STRUCTURE_ENTRIES
    filter_options = [QUAD_FILTERS, TRIPLE_FILTERS, DOUBLE_FILTERS,
                      ['htf_ema_trend', 'adx_trend'],
                      ['htf_ema_trend', 'obv_trend', 'adx_trend']]

    entry  = rng.choice(all_entries)
    fltrs  = list(rng.choice(filter_options))
    exit_m = rng.choice(ALL_EXITS)
    htf_bars = {'5m': rng.choice([48, 60, 72, 96]),
                '15m': rng.choice([16, 24, 32]),
                '1h': rng.choice([4, 6, 8]),
                '4h': 2}.get(tf, 48)

    p = {
        'st_period':       rng.randint(10, 30),
        'st_multiplier':   round(rng.uniform(1.5, 3.5), 1),
        'htf_bars':        htf_bars,
        'htf_ema_period':  rng.choice([20, 50, 100]),
        'atr_period':      14,
        'vol_ma_period':   rng.choice([20, 50]),
        'obv_period':      rng.choice([10, 20, 30]),
        'adx_period':      14,
        'adx_threshold':   rng.randint(20, 35),
        'ema_fast':        rng.randint(5, 15),
        'ema_slow':        rng.randint(20, 50),
        'ema_trend':       rng.choice([20, 50, 100]),
        'zscore_period':   rng.randint(10, 30),
        'zscore_threshold':round(rng.uniform(1.5, 3.0), 1),
        'sl_atr_mult':     round(rng.uniform(1.0, 3.0), 1),
        'tp_atr_mult':     round(rng.uniform(2.0, 8.0), 1),
        'tp_activation_mult': round(rng.uniform(0.8, 2.5), 1),
        'tp_trail_mult':   round(rng.uniform(0.5, 1.5), 1),
        'psar_acceleration': round(rng.uniform(0.01, 0.04), 3),
        'psar_maximum':    round(rng.uniform(0.1, 0.3), 2),
        'atr_multiplier':  round(rng.uniform(1.5, 3.5), 1),
        'intensity_period':rng.randint(10, 20),
        'taker_threshold': round(rng.uniform(0.55, 0.7), 2),
        'fr_long_thresh':  -0.0001,
        'fr_short_thresh':  0.0003,
        'coin': coin,
    }
    return {'name': f'rand_{entry}_{exit_m}', 'entry': entry, 'filters': fltrs,
            'exit': exit_m, 'params': p}


def _score_candidate(c: dict, df, date_from: str, date_to: str) -> dict:
    """Run backtest on one candidate and return scored result."""
    try:
        dna = StrategyDNA(df.copy(), c['entry'], c['filters'], c['exit'], c['params'])
        score, nm = score_dna(dna, df)
        result = {
            'score':         score,
            'total_return':  float(nm.get('Total Return',   -999) or -999),
            'sharpe':        float(nm.get('Sharpe Ratio',   -999) or -999),
            'total_trades':  int(nm.get('Total Trades',    0)),
            'profit_factor': float(nm.get('Profit Factor',    0) or 0),
            'max_drawdown':  abs(float(nm.get('Max Drawdown %', 100) or 100)),
        }
        return {**c, 'result': result}
    except Exception as e:
        return {**c, 'result': None, 'error': str(e)}


def _print_result(i: int, total: int, c: dict):
    r = c.get('result') or {}
    roi    = r.get('total_return', None)
    sharpe = r.get('sharpe', None)
    trades = r.get('total_trades', 0)
    pf     = r.get('profit_factor', None)
    roi_s  = f"{roi:+.2f}%" if roi is not None else "  N/A  "
    sh_s   = f"{sharpe:.3f}" if sharpe is not None else " N/A "
    pf_s   = f"{pf:.3f}" if pf is not None else " N/A "
    print(f"[{i:3d}/{total}] {c['name']:<30} ROI={roi_s}  Sharpe={sh_s}  Trades={trades:4d}  PF={pf_s}")


def _write_report(results: list, coin: str, tf: str, mode: str):
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f'{ts}_alpha_forge_{coin}_{tf}_{mode}.json'
    path  = os.path.join(REPORT_DIR, fname)

    good = [r for r in results if (r.get('result') or {}).get('sharpe', -99) >= 1.0]
    med  = [r for r in results if 0.3 <= (r.get('result') or {}).get('sharpe', -99) < 1.0]

    output = {
        'generated_at': datetime.now().isoformat(),
        'coin': coin, 'tf': tf, 'mode': mode,
        'total': len(results),
        'good': len(good), 'mediocre': len(med), 'bad': len(results) - len(good) - len(med),
        'results': sorted(results,
                          key=lambda r: (r.get('result') or {}).get('sharpe', -99),
                          reverse=True),
    }
    with open(path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    return path


def main():
    parser = argparse.ArgumentParser(description='Alpha Forge Search — new playstyle library')
    parser.add_argument('--coin',  default='ETH', choices=['BTC', 'ETH', 'BNB', 'SOL', 'XRP'])
    parser.add_argument('--tf',    default='5m',  choices=['5m', '15m', '1h', '4h', '1d'])
    parser.add_argument('--n',     type=int, default=100, help='Number of random candidates')
    parser.add_argument('--top',   type=int, default=10,  help='Top N results to print')
    parser.add_argument('--mode',  default='all',
                        choices=['all', 'trend', 'reversion', 'funding', 'presets'],
                        help='Entry mode filter')
    parser.add_argument('--date_from', default=None)
    parser.add_argument('--date_to',   default='2026-06-01')
    parser.add_argument('--seed',  type=int, default=42)
    args = parser.parse_args()

    # Date range by TF (developer standard from system_flow.md)
    if args.date_from is None:
        args.date_from = {
            '5m': '2023-01-01', '15m': '2024-05-31',
            '1h': '2023-05-31', '4h': '2023-05-31', '1d': '2022-05-31',
        }.get(args.tf, '2023-01-01')

    print(f"\n{'='*60}")
    print(f"  Alpha Forge Search | {args.coin} {args.tf} | {args.date_from}→{args.date_to}")
    print(f"  Mode: {args.mode} | Random: {args.n} | Seed: {args.seed}")
    print(f"{'='*60}\n")

    df = load_data(args.coin, args.tf, args.date_from, args.date_to)
    print(f"  Loaded {len(df):,} bars\n")

    rng = random.Random(args.seed)
    candidates = []

    # Always include hand-crafted presets
    candidates += _make_preset_candidates(args.tf, args.coin)

    # Add random candidates based on mode
    if args.mode in ('all', 'trend'):
        for _ in range(args.n // 2):
            c = _make_random_candidate(args.tf, args.coin, rng)
            c['entry'] = rng.choice(TREND_ENTRIES)
            c['name']  = f"rand_{c['entry']}_{c['exit']}"
            candidates.append(c)

    if args.mode in ('all', 'reversion'):
        for _ in range(args.n // 2):
            c = _make_random_candidate(args.tf, args.coin, rng)
            c['entry'] = rng.choice(REVERSION_ENTRIES)
            c['name']  = f"rand_{c['entry']}_{c['exit']}"
            candidates.append(c)

    if args.mode == 'funding':
        for exit_m in ALL_EXITS:
            candidates.append({
                'name': f'FR_mr_{exit_m}', 'entry': 'funding_rate_mr',
                'filters': ['adx_trend', 'atr_expansion'],
                'exit': exit_m,
                'params': {'fr_long_thresh': -0.0001, 'fr_short_thresh': 0.0003,
                           'adx_period': 14, 'adx_threshold': 20,
                           'atr_period': 14, 'vol_ma_period': 50,
                           'atr_multiplier': 2.5, 'tp_atr_mult': 5.0,
                           'sl_atr_mult': 2.0, 'tp_activation_mult': 1.5,
                           'tp_trail_mult': 0.8, 'coin': args.coin},
            })

    total = len(candidates)
    print(f"  Running {total} candidates...\n")

    results = []
    for i, c in enumerate(candidates, 1):
        scored = _score_candidate(c, df, args.date_from, args.date_to)
        results.append(scored)
        _print_result(i, total, scored)

    # Sort and print top N
    ranked = sorted(results, key=lambda r: (r.get('result') or {}).get('sharpe', -99), reverse=True)
    print(f"\n{'='*60}")
    print(f"  TOP {args.top} by Sharpe")
    print(f"{'='*60}")
    for c in ranked[:args.top]:
        r = c.get('result') or {}
        sh  = r.get('sharpe',       None)
        roi = r.get('total_return', None)
        mdd = r.get('max_drawdown', None)
        tr  = r.get('total_trades', 0)
        print(f"  {c['name']:<35} "
              f"Sharpe={sh:+.3f}  " if sh  is not None else f"  {c['name']:<35} Sharpe=  N/A   ",
              end='')
        print(f"ROI={roi:+.2f}%  " if roi is not None else "ROI=   N/A   ", end='')
        print(f"MDD={mdd:.2f}%  " if mdd is not None else "MDD=   N/A   ", end='')
        print(f"Trades={tr}")

    path = _write_report(results, args.coin, args.tf, args.mode)
    print(f"\n  Report saved: {path}\n")


if __name__ == '__main__':
    main()
