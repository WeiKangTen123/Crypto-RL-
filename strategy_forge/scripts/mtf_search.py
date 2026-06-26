"""
mtf_search.py — targeted search for low-MDD, moderate-return MTF strategies.

Targets:
  - Monthly profit: 2-3%
  - MDD: ~15%
  - Win rate: 40-50%
  - Trades: 3-7/week (~15-35/month on 1h)

Usage
-----
python strategy_forge/scripts/mtf_search.py --coin ETH --tf 1h --n 200
python strategy_forge/scripts/mtf_search.py --coin BTC --tf 1h --n 300 --score blend --top 10
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
from strategy_forge.runner.backtest_runner import score_dna, score_population
from strategy_forge.composer.random_compose import _ENTRY_PARAMS, _FILTER_PARAMS, _EXIT_PARAMS
from strategy_forge.params.ranges import sample_params

RESULTS_DIR = os.path.join(ROOT, 'strategy_forge', 'results')

# ── Hand-designed MTF candidates ─────────────────────────────────────────────
HAND_CRAFTED = [
    {
        'name': 'MTF_A: EMA_cross(1h) + HTF_EMA(4h) + ADX_trend | atr_tp_sl',
        'entry': 'ema_cross',
        'filters': ['htf_ema_trend', 'adx_trend'],
        'exit': 'atr_tp_sl',
        'params': {
            'ema_fast': 9, 'ema_slow': 21,
            'htf_bars': 4, 'htf_ema_period': 50,
            'adx_period': 14, 'adx_threshold': 20,
            'atr_period': 14, 'tp_atr_mult': 4.0, 'sl_atr_mult': 1.5,
        },
    },
    {
        'name': 'MTF_B: EMA_cross(1h) + HTF_Supertrend(4h) + WR_filter | atr_tp_sl',
        'entry': 'ema_cross',
        'filters': ['htf_supertrend', 'wr_not_extreme'],
        'exit': 'atr_tp_sl',
        'params': {
            'ema_fast': 9, 'ema_slow': 21,
            'htf_bars': 4, 'st_period': 10, 'st_multiplier': 3.0,
            'period': 14,
            'atr_period': 14, 'tp_atr_mult': 4.0, 'sl_atr_mult': 1.5,
        },
    },
    {
        'name': 'MTF_C: HMA_cross(1h) + HTF_EMA(4h) + WR_filter | atr_tp_sl',
        'entry': 'hma_cross',
        'filters': ['htf_ema_trend', 'wr_not_extreme'],
        'exit': 'atr_tp_sl',
        'params': {
            'ema_fast': 9, 'ema_slow': 34,
            'htf_bars': 4, 'htf_ema_period': 50,
            'period': 14,
            'atr_period': 14, 'tp_atr_mult': 3.5, 'sl_atr_mult': 1.5,
        },
    },
    {
        'name': 'MTF_D: EMA_cross(1h) + HTF_EMA(4h) + OBV_trend | supertrend_trail',
        'entry': 'ema_cross',
        'filters': ['htf_ema_trend', 'obv_trend'],
        'exit': 'supertrend_trail',
        'params': {
            'ema_fast': 8, 'ema_slow': 21,
            'htf_bars': 4, 'htf_ema_period': 50,
            'obv_period': 20,
            'st_period': 10, 'st_multiplier': 2.5,
        },
    },
    {
        'name': 'MTF_E: EMA_cross(1h) + HTF_Supertrend(4h) + ADX | chandelier_tp',
        'entry': 'ema_cross',
        'filters': ['htf_supertrend', 'adx_trend'],
        'exit': 'chandelier_tp',
        'params': {
            'ema_fast': 9, 'ema_slow': 21,
            'htf_bars': 4, 'st_period': 10, 'st_multiplier': 3.0,
            'adx_period': 14, 'adx_threshold': 20,
            'atr_period': 14, 'atr_multiplier': 3.0, 'tp_atr_mult': 4.0,
        },
    },
    {
        'name': 'MTF_F: ZLEMA_cross(1h) + HTF_EMA(4h) + ADX | atr_tp_sl',
        'entry': 'zlema_cross',
        'filters': ['htf_ema_trend', 'adx_trend'],
        'exit': 'atr_tp_sl',
        'params': {
            'ema_fast': 9, 'ema_slow': 21,
            'htf_bars': 4, 'htf_ema_period': 50,
            'adx_period': 14, 'adx_threshold': 20,
            'atr_period': 14, 'tp_atr_mult': 4.0, 'sl_atr_mult': 1.5,
        },
    },
    {
        'name': 'MTF_G: EMA_price_cross(1h) + HTF_EMA(4h) + WR | tight_atr',
        'entry': 'ema_price_cross',
        'filters': ['htf_ema_trend', 'wr_not_extreme'],
        'exit': 'tight_atr',
        'params': {
            'ema_period': 21,
            'htf_bars': 4, 'htf_ema_period': 50,
            'period': 14,
            'atr_period': 14, 'sl_atr_mult': 1.5, 'tp_atr_mult': 5.0,
        },
    },
    {
        'name': 'MTF_H: EMA_cross(1h) + HTF_EMA(4h) + ATR_expansion | atr_tp_sl',
        'entry': 'ema_cross',
        'filters': ['htf_ema_trend', 'atr_expansion'],
        'exit': 'atr_tp_sl',
        'params': {
            'ema_fast': 9, 'ema_slow': 21,
            'htf_bars': 4, 'htf_ema_period': 50,
            'atr_period': 14, 'vol_ma_period': 20,
            'tp_atr_mult': 4.0, 'sl_atr_mult': 1.5,
        },
    },
    {
        'name': 'MTF_I: Supertrend(1h) + HTF_EMA(4h) + OBV | chandelier_tp',
        'entry': 'supertrend',
        'filters': ['htf_ema_trend', 'obv_trend'],
        'exit': 'chandelier_tp',
        'params': {
            'st_period': 10, 'st_multiplier': 2.5,
            'htf_bars': 4, 'htf_ema_period': 100,
            'obv_period': 20,
            'atr_period': 14, 'atr_multiplier': 2.5, 'tp_atr_mult': 4.0,
        },
    },
    {
        'name': 'MTF_J: StochRSI(1h) + HTF_Supertrend(4h) + ADX | breakeven_trail',
        'entry': 'stoch_rsi_reversion',
        'filters': ['htf_supertrend', 'adx_trend'],
        'exit': 'breakeven_trail',
        'params': {
            'rsi_period': 14, 'smoothing': 3,
            'rsi_oversold': 20, 'rsi_overbought': 80,
            'htf_bars': 4, 'st_period': 10, 'st_multiplier': 3.0,
            'adx_period': 14, 'adx_threshold': 20,
            'atr_period': 14, 'sl_atr_mult': 1.0,
            'be_trigger_mult': 0.5, 'atr_multiplier': 2.0,
        },
    },
]

MTF_ENTRY_SIGNALS = [
    'ema_cross', 'ema_cross', 'ema_cross',
    'hma_cross', 'zlema_cross', 'ema_price_cross',
    'supertrend', 'aroon_cross',
    'stoch_rsi_reversion', 'wavetrend',
]
MTF_FILTERS = [
    'htf_ema_trend', 'htf_supertrend', 'htf_ema_trend',
    'obv_trend', 'wr_not_extreme', 'adx_trend', 'atr_expansion',
]
MTF_EXITS = [
    'atr_tp_sl', 'tight_atr', 'supertrend_trail',
    'chandelier_tp', 'atr_tp_sl_hold', 'breakeven_trail',
]


def _target_hit(tpw, mdd, wr, monthly):
    return (1.5 <= tpw <= 10) and (10 <= abs(mdd) <= 22) and (35 <= wr <= 55)


def main():
    parser = argparse.ArgumentParser(description='MTF Strategy Search — low-MDD, 2-3%/month target')
    parser.add_argument('--coin',        default='ETH',        help='Coin (BTC, ETH, SOL, ...)')
    parser.add_argument('--tf',          default='1h',         help='Base timeframe (default 1h)')
    parser.add_argument('--date_from',   default='2022-01-01')
    parser.add_argument('--date_to',     default='2026-06-01')
    parser.add_argument('--n',           type=int, default=200, help='Random search population size')
    parser.add_argument('--top',         type=int, default=10,  help='Top N to print')
    parser.add_argument('--score',       default='blend',       help='roi | sharpe | blend')
    parser.add_argument('--min_trades',  type=int, default=30)
    parser.add_argument('--risk',        type=float, default=0.05, help='risk_per_trade fraction')
    parser.add_argument('--leverage',    type=float, default=5.0)
    parser.add_argument('--seed',        type=int, default=99)
    args = parser.parse_args()

    RISK = dict(risk_per_trade=args.risk, leverage=args.leverage,
                trading_fee=0.0004, slippage_pct=0.0005)

    print(f"\n{'='*65}")
    print(f"  MTF Strategy Search — {args.coin} {args.tf}")
    print(f"  Target: 2-3%/mo | MDD ~15% | WR 40-50% | 3-7 trades/wk")
    print(f"  Risk: {args.risk} | leverage: {args.leverage}x | Score: {args.score}")
    print(f"{'='*65}\n")

    if args.coin.lower() == 'all':
        dataset_dir = os.path.join(ROOT, 'dataset')
        ignore_list = {'SPY', 'VIX', 'DXY', 'JPY'}
        coins_to_load = [d for d in os.listdir(dataset_dir) 
                         if os.path.isdir(os.path.join(dataset_dir, d)) 
                         and not d.startswith('.')
                         and d not in ignore_list]
    else:
        coins_to_load = [args.coin]

    df = {}
    for c in coins_to_load:
        try:
            df_c = load_data(c, args.tf, args.date_from, args.date_to)
            if df_c is not None and not df_c.empty:
                df[c] = df_c
        except Exception as e:
            pass # Skip folders like SPY/DXY or missing timeframes

    if not df:
        print('[ERROR] No data loaded.')
        sys.exit(1)
        
    if isinstance(df, dict) and len(df) == 1:
        # Revert to single dataframe if only 1 coin
        df = list(df.values())[0]

    if isinstance(df, dict):
        total_bars = sum(len(d) for d in df.values())
        print(f"Loaded {total_bars:,} total bars across {len(df)} coins.\n")
        sample_df = list(df.values())[0]
        weeks  = (sample_df.index[-1] - sample_df.index[0]).total_seconds() / (7 * 86400)
        months = weeks / 4.33
    else:
        print(f"Loaded {len(df):,} bars ({df.index[0].date()} → {df.index[-1].date()})\n")
        sample_df = df
        weeks  = (df.index[-1] - df.index[0]).total_seconds() / (7 * 86400)
        months = weeks / 4.33

    # ── Phase 1: Hand-crafted candidates ─────────────────────────────────────
    print("Phase 1: Hand-crafted MTF compositions...\n")
    p1_results = []
    for c in HAND_CRAFTED:
        dna = StrategyDNA(sample_df, c['entry'], c['filters'], c['exit'], c['params'])
        s, m = score_dna(dna, df, risk=RISK, score_mode=args.score,
                         min_trades=args.min_trades)
        trades  = int(m.get('Total Trades', 0) or 0)
        roi     = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
        sharpe  = float(str(m.get('Sharpe Ratio', '0')) or 0)
        mdd     = float(str(m.get('Max Drawdown %', '0')).replace('%', '') or 0)
        wr      = float(str(m.get('Win Rate', '0')).replace('%', '') or 0)
        tpw     = round(trades / weeks, 1) if weeks > 0 else 0
        monthly = round(roi / months, 2) if months > 0 else 0
        hit     = ' ← TARGET' if _target_hit(tpw, mdd, wr, monthly) else ''
        style   = m.get('style', '')
        print(f"  {c['name']}")
        print(f"    Score={s:.2f}  Sharpe={sharpe:.2f}  ROI={roi:.1f}%  Monthly={monthly:.2f}%"
              f"  MDD={mdd:.1f}%  WR={wr:.1f}%  Trades={trades} ({tpw}/wk)  [{style}]{hit}\n")
        p1_results.append((s, dna.to_dict(), m, c['name']))

    # ── Phase 2: Random MTF population ───────────────────────────────────────
    print(f"\nPhase 2: Random MTF search (n={args.n})...\n")
    rng = random.Random(args.seed)
    mtf_population = []
    for i in range(args.n):
        entry  = rng.choice(MTF_ENTRY_SIGNALS)
        mtf_f  = rng.choice(['htf_ema_trend', 'htf_supertrend'])
        sec_f  = rng.choice([f for f in MTF_FILTERS if f != mtf_f])
        exit_m = rng.choice(MTF_EXITS)

        param_names = list(set(
            _ENTRY_PARAMS.get(entry, []) +
            _FILTER_PARAMS.get(mtf_f, []) +
            _FILTER_PARAMS.get(sec_f, []) +
            _EXIT_PARAMS.get(exit_m, [])
        ))
        params = sample_params(param_names, seed=i * 7 + 13)
        params['htf_bars']    = rng.choice([2, 4, 4, 4, 8])
        params['tp_atr_mult'] = round(rng.uniform(1.8, 3.5), 2)
        params['sl_atr_mult'] = round(rng.uniform(0.8, 1.5), 2)
        if 'max_hold_bars' in params:
            params['max_hold_bars'] = rng.randint(12, 72)

        try:
            dna = StrategyDNA(sample_df, entry, [mtf_f, sec_f], exit_m, params)
            mtf_population.append(dna)
        except Exception:
            pass

    print(f"  Generated {len(mtf_population)} MTF DNAs\n")
    scored = score_population(mtf_population, df, risk=RISK,
                              score_mode=args.score, min_trades=args.min_trades,
                              verbose=True)

    # ── Final combined ranking ────────────────────────────────────────────────
    all_results = [(s, dna_d, m, src) for s, dna_d, m, src in p1_results]
    for s, dna, m in scored:
        if s > -999:
            all_results.append((s, dna.to_dict(), m, 'random'))
    all_results.sort(key=lambda x: -x[0])

    print(f"\n{'='*65}")
    print(f"  TOP {args.top} MTF STRATEGIES\n")
    for rank, (s, dna_d, m, src) in enumerate(all_results[:args.top], 1):
        trades  = int(m.get('Total Trades', 0) or 0)
        roi     = float(str(m.get('Total Return', '0')).replace('%', '') or 0)
        sharpe  = float(str(m.get('Sharpe Ratio', '0')) or 0)
        mdd     = float(str(m.get('Max Drawdown %', '0')).replace('%', '') or 0)
        wr      = float(str(m.get('Win Rate', '0')).replace('%', '') or 0)
        tpw     = round(trades / weeks, 1)
        monthly = round(roi / months, 2)
        style   = m.get('style', '')
        hit     = ' ← TARGET' if _target_hit(tpw, mdd, wr, monthly) else ''
        print(f"  #{rank:>2}  score={s:.2f}  [{src}]  [{style}]{hit}")
        print(f"       {dna_d['entry']} + {dna_d['filters']} → {dna_d['exit_method']}")
        print(f"       Sharpe={sharpe:.2f}  ROI={roi:.1f}%  Monthly={monthly:.2f}%"
              f"  MDD={mdd:.1f}%  WR={wr:.1f}%  {tpw:.1f}/wk")
        print()

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(RESULTS_DIR, f'mtf_search_{args.coin}_{args.tf}_{ts}.json')
    output = {
        'run_at':      datetime.now().isoformat(),
        'style':       'mtf',
        'coin':        args.coin,
        'tf':          args.tf,
        'date_from':   args.date_from,
        'date_to':     args.date_to,
        'n_tested':    len(mtf_population) + len(HAND_CRAFTED),
        'score_mode':  args.score,
        'risk':        RISK,
        'top_results': [
            {
                'rank':       rank,
                'score':      float(s),
                'source':     src,
                'entry':      d['entry'],
                'filters':    d['filters'],
                'exit_method':d['exit_method'],
                'params':     d['params'],
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
            for rank, (s, d, m, src) in enumerate(all_results[:args.top], 1)
        ],
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"  Results saved → {out_path}\n")


if __name__ == '__main__':
    main()
