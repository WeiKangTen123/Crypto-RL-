"""
scan_all.py — runs every registered strategy through the backtest engine
and writes graded results to data/scan_results.json.

Each strategy is scanned using its own date_from / date_to from settings.py
so results match exactly what Phase 4 would show.
The --date_from / --date_to CLI args act as a fallback for strategies
that have no date range configured in settings.py.

Usage:
    python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py
    python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py --date_from 2021-01-01 --date_to 2026-12-31
    python .gemini/skills/crypto-strategy-tuner/scripts/scan_all.py --new-only
"""

import os
import sys
import json
import argparse
from datetime import datetime

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
AGENT_DIR  = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner')
OUTPUT     = os.path.join(AGENT_DIR, 'data', 'scan_results.json')

sys.path.insert(0, ROOT_DIR)

# Import grading function from classify_strategies so scan auto-grades immediately.
sys.path.insert(0, os.path.join(AGENT_DIR, 'scripts'))
try:
    from classify_strategies import grade_strategy as _grade_strategy
except Exception:
    _grade_strategy = None


def run_scan(date_from='2021-01-01', date_to='2026-12-31', new_only=False):
    from strategy_backtest.settings     import STRATEGY_LIBRARY
    from strategy_backtest.engine       import BacktestEngine
    from strategy_backtest.risk         import RiskManager
    from strategy_backtest.metrics      import compute_metrics
    from strategy_backtest.run_backtest import load_data
    import strategy_backtest.strategies as strat_reg
    from strategy_backtest.metrics import compute_metrics, _extract_numeric

    # Load existing results so we can preserve them in new-only mode
    existing_results = []
    existing_ids     = set()
    if new_only and os.path.exists(OUTPUT):
        try:
            with open(OUTPUT) as f:
                existing_data = json.load(f)
            existing_results = existing_data.get('results', [])
            existing_ids     = {str(r['id']) for r in existing_results}
        except Exception:
            existing_results, existing_ids = [], set()

    all_sids   = sorted(STRATEGY_LIBRARY.keys(), key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else 9999)
    to_scan    = [sid for sid in all_sids if sid not in existing_ids] if new_only else all_sids
    skip_count = len(existing_ids) if new_only else 0

    if new_only:
        print(f'NEW-ONLY mode: {skip_count} already scanned, {len(to_scan)} new to scan.\n')
    else:
        print(f'Scanning {len(to_scan)} strategies (each uses its own configured date range, fallback {date_from} → {date_to})...\n')

    if not to_scan:
        print('No new strategies found — scan_results.json is up to date.')
        return existing_data if new_only else {}

    new_results = []
    total       = len(to_scan)
    for idx, sid in enumerate(to_scan, 1):
        cfg = STRATEGY_LIBRARY[sid]
        # Use the strategy's own configured period; fall back to CLI args if not set
        strat_date_from = cfg['data'].get('date_from') or date_from
        strat_date_to   = cfg['data'].get('date_to')   or date_to

        print(f'  [{idx}/{total}] ID={sid} {cfg["class"]} ({cfg["data"].get("coins","?")} / {cfg["data"].get("timeframes","?")} | {strat_date_from} → {strat_date_to})', end=' ... ', flush=True)
        entry = {
            'id':         sid,
            'class':      cfg['class'],
            'coin':       cfg['data'].get('coins', '?'),
            'tf':         cfg['data'].get('timeframes', '?'),
            'params':     cfg.get('params', {}),
            'scanned_at': datetime.now().isoformat(),
            'date_from':  strat_date_from,
            'date_to':    strat_date_to,
        }
        try:
            # Pre-scan check: verify required supplementary data files exist
            candle_types = cfg['data'].get('candle_types', [])
            if candle_types:
                coin = cfg['data']['coins']
                tf   = cfg['data']['timeframes']
                for ct in candle_types:
                    ct_path = os.path.join(ROOT_DIR, 'dataset', coin, tf, f'{ct}.parquet')
                    if not os.path.exists(ct_path):
                        raise FileNotFoundError(
                            f"Required data file missing: dataset/{coin}/{tf}/{ct}.parquet — "
                            f"run funding_rate_fetcher.py or sync_all.py first"
                        )

            df = load_data(cfg['data']['coins'], cfg['data']['timeframes'], strat_date_from, strat_date_to)
            if df is None or df.empty or len(df) < 50:
                raise ValueError('Insufficient data')

            strat_cls = getattr(strat_reg, cfg['class'], None)
            if strat_cls is None:
                raise ImportError(f'Class {cfg["class"]} not found in strategies module')

            rm = RiskManager(
                risk_per_trade=cfg['risk']['risk_per_trade'],
                leverage=cfg['risk']['leverage'],
                trading_fee=cfg['risk']['trading_fee'],
                slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
                maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
            )
            engine = BacktestEngine(
                df, strat_cls(df, **cfg.get('params', {})), rm,
                initial_balance=cfg['risk']['initial_balance']
            )
            equity = engine.run()
            if not equity or len(equity) < 2:
                raise ValueError('Empty equity curve')

            m               = compute_metrics(equity, cfg['risk']['initial_balance'],
                                             timestamps=engine.df.index, trades=engine.trades)
            numeric_metrics = _extract_numeric(m)

            sharpe = round(numeric_metrics.get('Sharpe Ratio', 0), 3)
            entry.update({
                'sharpe':        sharpe,
                'total_return':  round(numeric_metrics.get('Total Return', 0), 1),
                'max_drawdown':  round(numeric_metrics.get('Max Drawdown %', 0), 1),
                'win_rate':      round(numeric_metrics.get('Win Rate', 0), 1),
                'total_trades':  int(numeric_metrics.get('Total Trades', 0)),
                'profit_factor': round(numeric_metrics.get('Profit Factor', 0), 2),
                'grade':         'PENDING',
                'grade_reason':  None,
                'error':         None,
            })
            # Auto-grade immediately using classify_strategies rules (no agent quota needed)
            if _grade_strategy is not None:
                try:
                    g, reason = _grade_strategy(entry)
                    entry['grade']        = g
                    entry['grade_reason'] = reason
                    print(f'Sharpe={sharpe:.2f}  → {g} | {reason[:60]}')
                except Exception:
                    print(f'Sharpe={sharpe:.2f}  [PENDING — auto-grade failed]')
            else:
                print(f'Sharpe={sharpe:.2f}  [PENDING — awaiting agent classification]')

        except Exception as e:
            entry.update({
                'sharpe':        None,
                'total_return':  None,
                'max_drawdown':  None,
                'win_rate':      None,
                'total_trades':  None,
                'profit_factor': None,
                'grade':         'ERROR',
                'error':         str(e)[:300],
            })
            print(f'ERROR — {e}')

        new_results.append(entry)

    # Merge: existing untouched entries + newly scanned entries
    all_results = existing_results + new_results
    counts = {g: sum(1 for r in all_results if r['grade'] == g)
              for g in ('GOOD', 'MEDIOCRE', 'BAD', 'PENDING', 'ERROR')}

    # classified=True when no PENDING remain (auto-grade resolved all new ones)
    all_classified = counts.get('PENDING', 0) == 0
    output = {
        'scanned_at':      datetime.now().isoformat(),
        'date_range':      'per-strategy (from settings.py)',
        'fallback_from':   date_from,
        'fallback_to':     date_to,
        'total':           len(all_results),
        'classified':      all_classified,
        'classified_at':   datetime.now().isoformat() if all_classified else None,
        **counts,
        'results':         all_results,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)

    print(f'\nScan+Grade complete → {len(new_results)} new  |  GOOD={counts.get("GOOD",0)}  MEDIOCRE={counts.get("MEDIOCRE",0)}  BAD={counts.get("BAD",0)}  PENDING={counts.get("PENDING",0)}  ERROR={counts.get("ERROR",0)}')
    print(f'Results saved to {OUTPUT}')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan all registered strategies')
    parser.add_argument('--date_from', default='2021-01-01', help='Fallback start date for strategies with no date_from in settings.py')
    parser.add_argument('--date_to',   default='2026-12-31', help='Fallback end date for strategies with no date_to in settings.py')
    parser.add_argument('--new-only',  action='store_true',  help='Only scan strategy IDs not already in scan_results.json')
    args = parser.parse_args()
    run_scan(args.date_from, args.date_to, new_only=args.new_only)
