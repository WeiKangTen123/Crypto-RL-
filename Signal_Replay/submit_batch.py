"""
Signal Replay batch submitter.

Runs a strategy locally through strategy_backtest's real engine (single-coin
BacktestEngine or multi-coin PortfolioBacktestEngine), converts the actual
trade events into a Signal Replay signal series (one entry per position
change), and POSTs it to the Signal Strive API. Every signal is tagged with
margin+leverage (from the strategy's own STRATEGY_LIBRARY risk config) so one
submission scores both Run A (platform's standard sizing, grade of record)
and Run B (our own sizing) in a single call.

Usage:
    python Signal_Replay/submit_batch.py --list 222-240              # dry run, no network
    python Signal_Replay/submit_batch.py --strategy 222 --dry-run     # inspect one payload
    python Signal_Replay/submit_batch.py --strategy 222               # submit one, live
    python Signal_Replay/submit_batch.py --list 222-240 --live        # submit the whole batch
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from strategy_backtest.settings import STRATEGY_LIBRARY
from strategy_backtest.run_backtest import load_data
from strategy_backtest.risk import RiskManager
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.portfolio_engine import PortfolioBacktestEngine
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
import strategy_backtest.strategies as strat_reg

SIGNAL_REPLAY_DIR = Path(__file__).parent
API_KEY_FILE = SIGNAL_REPLAY_DIR.parent / 'API & others' / 'signal_replay_api.txt'
RUNS_FILE = SIGNAL_REPLAY_DIR / 'runs.json'
API_URL = 'http://47.237.70.198:5300/api/v1/signals'
RUN_B_BASE_CAPITAL = 1_000_000  # matches the convention used for prior submissions

# WorldQuant Alpha resolution mapping — API docs list 1m|5m|15m|1h|1d but prior
# 4h submissions (e.g. #56 ETH/4h) were accepted and graded, so pass through as-is.


def load_api_key() -> str:
    return API_KEY_FILE.read_text().strip().split('=', 1)[-1].strip()


def run_local_backtest(sid: str):
    """Run the strategy locally and return (cfg, trades, is_multi_coin)."""
    cfg = STRATEGY_LIBRARY[sid]
    d = cfg['data']
    r = cfg['risk']
    params = cfg.get('params', {})

    coins = d.get('coins', d.get('symbols', 'BTC'))
    tf = d['timeframes']
    is_multi_coin = isinstance(coins, list) and len(coins) > 1

    data = load_data(coins, tf, d['date_from'], d['date_to'], mode='portfolio')

    strat_cls = getattr(strat_reg, cfg['class'])
    strategy = strat_cls(data, **params)

    rm = RiskManager(
        risk_per_trade=r.get('risk_per_trade'),
        leverage=r['leverage'],
        trading_fee=r['trading_fee'],
        maintenance_margin_rate=r['maintenance_margin_rate'],
        frequency=tf,
    )

    if is_multi_coin:
        if not issubclass(strat_cls, MultiCoinBaseStrategy):
            raise TypeError(f"{cfg['class']} must inherit MultiCoinBaseStrategy for portfolio mode")
        engine = PortfolioBacktestEngine(data, strategy, rm, initial_balance=r['initial_balance'])
    else:
        engine = BacktestEngine(data, strategy, rm, initial_balance=r['initial_balance'])

    engine.run()
    return cfg, engine.trades, is_multi_coin


def trades_to_targets(trades, default_symbol: str):
    """
    Convert engine.trades (chronological BUY/SELL/BUY_ADD/SELL_ADD/EXIT_LONG/
    EXIT_SHORT events — SL/TP/LIQUIDATION/EXIT/REVERSE all funnel through
    EXIT_LONG/EXIT_SHORT, tagged by 'reason') into one signal per real
    position change: {ts (pd.Timestamp), symbol, target}.

    Every real state transition must survive, including same-bar
    close-then-reopen pairs (e.g. REVERSE, or an SL/TP exit immediately
    followed by a fresh entry on the same bar) — otherwise a local flatten
    event gets silently erased and the platform's replay never learns we
    wanted out, which is what was driving the liquidation-cascade fill
    inflation (target stays "stuck" active, so a forced liquidation on their
    side just re-opens to match our still-unchanged target, repeatedly).
    sorted() is stable and engine.trades already appends closes before opens
    within a bar, so iterating in order and emitting on every real state
    change (rather than deduping by (symbol, ts)) preserves both events.
    """
    ordered = sorted(trades, key=lambda x: x['time'])

    events = []
    running = {}
    for t in ordered:
        sym = t.get('symbol', default_symbol)
        typ = t['type']
        if typ in ('BUY', 'BUY_ADD'):
            target = 1.0
        elif typ in ('SELL', 'SELL_ADD'):
            target = -1.0
        elif typ in ('EXIT_LONG', 'EXIT_SHORT'):
            target = 0.0
        else:
            continue
        if running.get(sym) == target:
            continue
        running[sym] = target
        events.append({'ts': t['time'], 'symbol': sym, 'target': target})
    return events


def build_payload(cfg: dict, events: list) -> dict:
    d = cfg['data']
    r = cfg['risk']
    coins = d.get('coins', d.get('symbols', ['BTC']))
    n_coins = len(coins) if isinstance(coins, list) else 1
    leverage = r['leverage']

    # Multi-coin submissions share ONE cross-margin book capped at 3x gross
    # exposure / 95% equity per position (see usage.MD). Sizing margin off
    # risk_per_trade alone (as if only one coin could ever be open) lets
    # aggregate notional blow past that cap whenever several coins are open
    # at once, which appears to trigger platform-side rebalancing fills far
    # in excess of our actual signal count. Dividing by n_coins keeps total
    # exposure roughly constant (~0.15x gross here) even if every coin in
    # the book is simultaneously open, well under the 3x cap.
    margin = round(r.get('risk_per_trade', 0.05) * RUN_B_BASE_CAPITAL / n_coins, 2)

    # strength scales Run A's own bet size ("we size it" — margin/leverage above
    # are Run-B-only and provably don't touch Run A). Without it, Run A may
    # default to full conviction on every signal; scale down by n_coins the
    # same way margin is, in case full conviction across many simultaneously
    # open coins is what's breaching the shared book's exposure cap.
    strength = round(1.0 / n_coins, 3)

    signals = [{
        'ts': int(e['ts'].value),  # pandas Timestamp.value is already ns since epoch
        'symbol': f"{e['symbol']}USDT",
        'target': e['target'],
        'strength': strength,
        'margin': margin,
        'leverage': leverage,
    } for e in events]

    return {
        'strategy': cfg.get('id', 'Vegas_ZScore'),
        'resolution': d['timeframes'],
        'start': d['date_from'],
        'end': d['date_to'],
        'signals': signals,
    }


def submit(payload: dict, api_key: str) -> dict:
    endpoints = [
        'https://btest.abcz-tr.com/api/v1/signals',
        'http://47.237.70.198:5300/api/v1/signals'
    ]
    last_err = None
    for url in endpoints:
        try:
            print(f"Submitting to {url}...")
            resp = requests.post(
                url,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Endpoint {url} failed: {e}")
            last_err = e
            continue
    raise last_err


def process_strategy(sid: str, api_key: str, dry_run: bool = True) -> dict:
    cfg, trades, is_multi = run_local_backtest(sid)
    default_symbol = cfg['data'].get('coins', cfg['data'].get('symbols', 'BTC'))
    if isinstance(default_symbol, list):
        default_symbol = default_symbol[0]

    events = trades_to_targets(trades, default_symbol)
    payload = build_payload(cfg, events)

    summary = {
        'strategy_id': sid,
        'class': cfg['class'],
        'desc': cfg.get('desc'),
        'coins': cfg['data'].get('coins', cfg['data'].get('symbols')),
        'timeframe': cfg['data']['timeframes'],
        'n_local_trades': len(trades),
        'n_signal_events': len(events),
        'window': f"{cfg['data']['date_from']} -> {cfg['data']['date_to']}",
    }

    if dry_run:
        summary['status'] = 'DRY_RUN'
        summary['payload_preview'] = {
            'resolution': payload['resolution'],
            'start': payload['start'],
            'end': payload['end'],
            'n_signals': len(payload['signals']),
            'first_signal': payload['signals'][0] if payload['signals'] else None,
            'last_signal': payload['signals'][-1] if payload['signals'] else None,
        }
        return summary

    if not events:
        summary['status'] = 'SKIPPED_NO_TRADES'
        return summary

    response = submit(payload, api_key)
    summary['status'] = 'SUBMITTED'
    summary['response'] = response
    return summary


def parse_id_range(spec: str):
    if '-' in spec:
        lo, hi = spec.split('-')
        return [str(i) for i in range(int(lo), int(hi) + 1)]
    return [spec]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--strategy', help='single strategy id, e.g. 222')
    ap.add_argument('--list', help='id range, e.g. 222-240')
    ap.add_argument('--dry-run', action='store_true', help='build payload but do not POST')
    ap.add_argument('--live', action='store_true', help='required alongside --list to actually submit the batch')
    args = ap.parse_args()

    ids = []
    if args.strategy:
        ids = [args.strategy]
    elif args.list:
        ids = parse_id_range(args.list)
    else:
        ap.error('provide --strategy or --list')

    dry = args.dry_run or (args.list and not args.live)
    api_key = load_api_key()

    results = []
    for sid in ids:
        print(f"\n=== #{sid} ===")
        try:
            res = process_strategy(sid, api_key, dry_run=dry)
        except Exception as e:
            res = {'strategy_id': sid, 'status': 'ERROR', 'error': str(e)}
        print(json.dumps(res, indent=2, default=str))
        results.append(res)

    out_file = SIGNAL_REPLAY_DIR / f'batch_output_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved batch output to {out_file}")
