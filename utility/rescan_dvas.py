"""
rescan_dvas.py
Re-scans strategy IDs 157 and 158 (DVASStrategy) with the current settings.py
params and the corrected SL-first execution logic, then patches scan_results.json
in place so only those two entries are updated.
"""

import os, sys, json
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, '.gemini', 'skills', 'crypto-strategy-tuner', 'scripts'))

SCAN_FILE = os.path.join(ROOT, '.gemini', 'skills', 'crypto-strategy-tuner', 'data', 'scan_results.json')
TARGET_IDS = ['157', '158']

from strategy_backtest.settings     import STRATEGY_LIBRARY
from strategy_backtest.engine       import BacktestEngine
from strategy_backtest.risk         import RiskManager
from strategy_backtest.metrics      import compute_metrics, _extract_numeric
from strategy_backtest.run_backtest import load_data
import strategy_backtest.strategies as strat_reg

try:
    from classify_strategies import grade_strategy
except ImportError:
    grade_strategy = None

data = json.load(open(SCAN_FILE))
results = data.get('results', [])
results_by_id = {str(r['id']): i for i, r in enumerate(results)}

for sid in TARGET_IDS:
    cfg = STRATEGY_LIBRARY[sid]
    strat_date_from = cfg['data'].get('date_from', '2023-01-01')
    strat_date_to   = cfg['data'].get('date_to',   '2026-06-01')

    print(f'[{sid}] {cfg["class"]} ({cfg["data"]["coins"]} / {cfg["data"]["timeframes"]}) '
          f'{strat_date_from} → {strat_date_to}', flush=True)

    df = load_data(cfg['data']['coins'], cfg['data']['timeframes'], strat_date_from, strat_date_to)
    strat_cls = getattr(strat_reg, cfg['class'])
    rm = RiskManager(
        risk_per_trade=cfg['risk']['risk_per_trade'],
        leverage=cfg['risk']['leverage'],
        trading_fee=cfg['risk']['trading_fee'],
        slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
        maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
    )
    engine = BacktestEngine(df, strat_cls(df, **cfg.get('params', {})), rm,
                            initial_balance=cfg['risk']['initial_balance'])
    equity = engine.run()
    m      = compute_metrics(equity, cfg['risk']['initial_balance'],
                             timestamps=engine.df.index, trades=engine.trades)
    nm     = _extract_numeric(m)

    sharpe       = round(nm.get('Sharpe Ratio', 0), 3)
    total_return = round(nm.get('Total Return', 0), 1)
    max_dd       = round(nm.get('Max Drawdown %', 0), 1)
    win_rate     = round(nm.get('Win Rate', 0), 1)
    trades_count = int(nm.get('Total Trades', 0))
    pf           = round(nm.get('Profit Factor', 0), 2)

    print(f'  Sharpe={sharpe}  Return={total_return}%  MDD={max_dd}%  '
          f'WinRate={win_rate}%  Trades={trades_count}  PF={pf}')

    entry = {
        'id':           sid,
        'class':        cfg['class'],
        'coin':         cfg['data'].get('coins', '?'),
        'tf':           cfg['data'].get('timeframes', '?'),
        'params':       cfg.get('params', {}),
        'scanned_at':   datetime.now(timezone.utc).isoformat(),
        'date_from':    strat_date_from,
        'date_to':      strat_date_to,
        'sharpe':       sharpe,
        'total_return': total_return,
        'max_drawdown': max_dd,
        'win_rate':     win_rate,
        'total_trades': trades_count,
        'profit_factor': pf,
        'error':        None,
    }

    # Grade
    if grade_strategy:
        grade, reason = grade_strategy(entry)
        entry['grade'] = grade
        entry['grade_reason'] = reason
        print(f'  Grade: {grade} — {reason}')
    else:
        if sharpe >= 1.0 and trades_count >= 100 and max_dd <= 70:
            entry['grade'] = 'GOOD'
        elif sharpe >= 0.3 and trades_count >= 30:
            entry['grade'] = 'MEDIOCRE'
        else:
            entry['grade'] = 'BAD'
        entry['grade_reason'] = f'SL-first execution. Sharpe {sharpe}, {trades_count} trades.'
        print(f'  Grade: {entry["grade"]}')

    # Patch in place
    if sid in results_by_id:
        results[results_by_id[sid]] = entry
    else:
        results.append(entry)

# Recount grades
good     = sum(1 for r in results if r.get('grade') == 'GOOD')
mediocre = sum(1 for r in results if r.get('grade') == 'MEDIOCRE')
bad      = sum(1 for r in results if r.get('grade') == 'BAD')

data['results']         = results
data['classified_at']   = datetime.now(timezone.utc).isoformat()
data['GOOD']            = good
data['MEDIOCRE']        = mediocre
data['BAD']             = bad

with open(SCAN_FILE, 'w') as f:
    json.dump(data, f, indent=2)

print(f'\nDone. scan_results.json patched. GOOD={good} MEDIOCRE={mediocre} BAD={bad}')
