"""
Runs the remaining strategies through submit_batch.py's pipeline and appends
compact runs.json-style records (matching the schema of prior submissions)
incrementally, so progress isn't lost if a later strategy fails.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

SIGNAL_REPLAY_DIR = Path(__file__).parent
sys.path.insert(0, str(SIGNAL_REPLAY_DIR))
from submit_batch import process_strategy, load_api_key

RUNS_FILE = SIGNAL_REPLAY_DIR / 'runs.json'


def grade_pts(grade):
    return {'A': 90, 'B': 75, 'C': 60, 'D': 45, 'F': 20}.get(grade, 0)


def gap_verdict(run_a, run_b):
    if not run_b:
        return 'Run B not available (scheme not faithfully applied or missing).'
    a_score, b_score = run_a['score'], run_b['score']
    delta_pts = round(b_score - a_score, 1)
    a_ret, b_ret = run_a['total_return_pct'], run_b['total_return_pct']
    delta_ret = round(b_ret - a_ret, 1)
    direction = 'helped' if delta_pts > 2 else 'hurt' if delta_pts < -2 else '≈ neutral vs standard'
    return (f"Provider sizing {direction} ({delta_pts:+.1f} pts, {run_b['grade']} vs {run_a['grade']}) "
            f"— return {delta_ret:+.1f}pp.")


def to_compact_record(sid, cfg, response):
    dims = {d['key']: {'score': d['score'], 'grade': d['grade']} for d in response['scorecard'].get('dimensions', [])}
    sizing = response.get('sizing', {})
    run_a_raw = sizing.get('run_a', {})
    run_b_raw = sizing.get('run_b')

    run_a = {
        'grade': run_a_raw.get('grade', response.get('grade')),
        'score': run_a_raw.get('score', response.get('overall_score')),
        'return_pct': round(run_a_raw.get('total_return', response.get('total_return', 0)) * 100, 1),
        'sharpe': round(run_a_raw.get('sharpe', response.get('sharpe', 0)), 3),
        'mdd_pct': round(run_a_raw.get('max_drawdown', response.get('max_drawdown', 0)) * 100, 1),
        'final_equity': round(run_a_raw.get('final_equity_usd', response.get('final_equity_usd', 0))),
        'n_fills': run_a_raw.get('n_fills', response.get('n_fills')),
        'lens': response.get('lens'),
    }

    run_b = None
    if run_b_raw:
        run_b = {
            'grade': run_b_raw.get('grade'),
            'score': run_b_raw.get('score'),
            'return_pct': round(run_b_raw.get('total_return', 0) * 100, 1),
            'sharpe': round(run_b_raw.get('sharpe', 0), 3),
            'mdd_pct': round(run_b_raw.get('max_drawdown', 0) * 100, 1),
            'final_equity': round(run_b_raw.get('final_equity_usd', 0)),
        }

    verdict = gap_verdict(
        {'score': run_a['score'], 'total_return_pct': run_a['return_pct'], 'grade': run_a['grade']},
        {'score': run_b['score'], 'total_return_pct': run_b['return_pct'], 'grade': run_b['grade']} if run_b else None,
    )

    coins = cfg['data'].get('coins', cfg['data'].get('symbols'))
    coin_label = '+'.join(coins) if isinstance(coins, list) else coins

    return {
        'run_id': response.get('run_id'),
        'strat_id': sid,
        'name': cfg.get('desc', cfg['class']),
        'class': cfg['class'],
        'coin': coin_label,
        'tf': cfg['data']['timeframes'],
        'symbol': response.get('symbol'),
        'symbols_covered': response.get('symbols'),
        'uncovered_symbols': response.get('uncovered_symbols'),
        'submitted_at': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'risk_used': {
            'risk_per_trade': cfg['risk'].get('risk_per_trade'),
            'leverage': cfg['risk']['leverage'],
            'trading_fee': cfg['risk']['trading_fee'],
        },
        'run_a': run_a,
        'run_b': run_b,
        'gap_verdict': verdict,
        'scorecard': dims,
    }


def main(ids):
    api_key = load_api_key()
    runs_data = json.loads(RUNS_FILE.read_text())

    for sid in ids:
        print(f"\n=== Submitting #{sid} ===")
        try:
            result = process_strategy(sid, api_key, dry_run=False)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        if result['status'] != 'SUBMITTED':
            print(f"  status={result['status']}, skipping record")
            continue

        from strategy_backtest.settings import STRATEGY_LIBRARY
        cfg = STRATEGY_LIBRARY[sid]
        record = to_compact_record(sid, cfg, result['response'])
        runs_data['runs'].append(record)
        RUNS_FILE.write_text(json.dumps(runs_data, indent=2))

        print(f"  run_id={record['run_id']} grade_A={record['run_a']['grade']} "
              f"score_A={record['run_a']['score']} grade_B={record['run_b']['grade'] if record['run_b'] else 'N/A'}")

    print(f"\nDone. Total runs recorded: {len(runs_data['runs'])}")


if __name__ == '__main__':
    ids = sys.argv[1:] if len(sys.argv) > 1 else []
    main(ids)
