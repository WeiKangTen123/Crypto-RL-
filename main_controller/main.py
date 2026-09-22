import os
import sys
import glob
import re
import subprocess
import json
import signal
import threading
import requests as _requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context

app = Flask(__name__)

# Wire Werkzeug access/error logs to server.log (persists regardless of how Flask is launched)
import logging as _logging
_wz_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.log')
_wz_handler = _logging.FileHandler(_wz_log_path, mode='a', encoding='utf-8')
_wz_handler.setFormatter(_logging.Formatter('%(asctime)s %(message)s', datefmt='[%Y-%m-%d %H:%M:%S]'))
_logging.getLogger('werkzeug').addHandler(_wz_handler)
_logging.getLogger('werkzeug').setLevel(_logging.INFO)
del _wz_handler, _wz_log_path

# Path Configuration
CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CONTROLLER_DIR)

# --- START PATCH ---
# Add the parent of the nested 'freqtrade' directory to the path to resolve imports
# like 'freqtrade.strategy'. The 'freqtrade' submodule is inside the main 'freqtrade' dir.
_FREQTRADE_MODULE_PATH = os.path.join(ROOT_DIR, 'freqtrade')
if _FREQTRADE_MODULE_PATH not in sys.path:
    sys.path.insert(0, _FREQTRADE_MODULE_PATH)
# --- END PATCH ---

STATE_FILE = os.path.join(CONTROLLER_DIR, 'pipeline_state.json')
VENV_PYTHON = os.path.join(ROOT_DIR, 'venv', 'bin', 'python')

# Global process tracker
active_processes = {}

# Inbox snapshot — tracks which files were present last poll so we can archive resolved ones
_inbox_snapshot = {}

def _archive_resolved_inbox(current_msgs):
    """Detect inbox messages that were read/deleted since last poll and archive them."""
    global _inbox_snapshot
    resolved_path = os.path.join(ROOT_DIR, '.gemini', 'shared', 'resolved_inbox.jsonl')
    current_files = {m.get('_file', ''): m for m in current_msgs if m.get('_file')}
    for fname, msg in _inbox_snapshot.items():
        if fname not in current_files:
            msg['_resolved_at'] = datetime.now().isoformat()
            try:
                with open(resolved_path, 'a') as f:
                    f.write(json.dumps(msg) + '\n')
            except Exception:
                pass
    _inbox_snapshot = dict(current_files)

def _get_resolved_inbox(n=15):
    """Return last n resolved (read and deleted) inbox messages."""
    resolved_path = os.path.join(ROOT_DIR, '.gemini', 'shared', 'resolved_inbox.jsonl')
    if not os.path.exists(resolved_path):
        return []
    with open(resolved_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    msgs = []
    for line in reversed(lines):
        try:
            msgs.append(json.loads(line))
        except Exception:
            pass
        if len(msgs) >= n:
            break
    return msgs

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"phases": {}, "latest_results": {}}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def refresh_metadata():
    state = load_state()
    project_root = ROOT_DIR
    data_dir = os.path.join(project_root, 'data')
    
    # Check Phase 0 Trainval
    if os.path.exists(data_dir):
        # Find the most recent timeframe folder
        subdirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)) and d != 'trade_data']
        if subdirs:
            subdirs.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)), reverse=True)
            meta_path = os.path.join(data_dir, subdirs[0], 'metadata.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    state['phases']['phase_0_trainval']['metadata'] = json.load(f)

    # Check Phase 0 Trade
    trade_dir = os.path.join(data_dir, 'trade_data')
    if os.path.exists(trade_dir):
        subdirs = [d for d in os.listdir(trade_dir) if os.path.isdir(os.path.join(trade_dir, d))]
        if subdirs:
            subdirs.sort(key=lambda x: os.path.getmtime(os.path.join(trade_dir, x)), reverse=True)
            meta_path = os.path.join(trade_dir, subdirs[0], 'metadata.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    state['phases']['phase_0_trade']['metadata'] = json.load(f)
    
    save_state(state)

def update_phase_status(phase, status, last_run=None):
    state = load_state()
    if phase in state['phases']:
        state['phases'][phase]['status'] = status
        if last_run:
            state['phases'][phase]['last_run'] = last_run
        save_state(state)

@app.route('/')
def index():
    return send_from_directory(CONTROLLER_DIR, 'index.html')

@app.after_request
def add_header(response):
    response.headers['Content-Security-Policy'] = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data:; "
        "script-src * 'unsafe-inline' 'unsafe-eval' data:; "
        "style-src * 'unsafe-inline' 'unsafe-eval'; "
        "img-src * data: blob:; "
        "font-src * data:;"
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


_ERROR_LOG = os.path.join(ROOT_DIR, '.gemini', 'logs', 'error_log.jsonl')
_AGENT_STATUS = os.path.join(ROOT_DIR, 'main_controller', 'agent_status.json')

def _write_error_log(error_msg: str):
    """Append a structured error entry to the debugger error log."""
    entry = {
        'ts':    datetime.now().isoformat(),
        'error': error_msg,
    }
    try:
        os.makedirs(os.path.dirname(_ERROR_LOG), exist_ok=True)
        with open(_ERROR_LOG, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass

def _write_agent_status(status: str, detail: str = ''):
    try:
        with open(_AGENT_STATUS, 'w') as f:
            json.dump({'status': status, 'detail': detail,
                       'ts': datetime.now().isoformat()}, f, indent=2)
    except Exception:
        pass

def trigger_gemini_debugger(error_msg: str):
    """Write error to inbox of @crypto-fullstack to trigger autonomous fix."""
    _write_error_log(error_msg)
    _write_agent_status('Triggering Agent...', error_msg[:120])
    
    inbox_dir = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-fullstack', 'inbox')
    os.makedirs(inbox_dir, exist_ok=True)
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    payload = {
        'from': 'System_Server',
        'priority': 'HIGH',
        'topic': 'RUNTIME_ERROR_DETECTED',
        'message': f"A runtime error occurred: {error_msg}",
        'ts': datetime.now().isoformat()
    }
    
    try:
        with open(os.path.join(inbox_dir, f"{ts}_error.json"), 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"  [AGENT] Error dispatched to crypto-fullstack inbox.")
    except Exception as e:
        print(f"  [ERROR] Failed to dispatch error to agent: {e}")

# keep old name as alias so existing call-sites still work
trigger_claude_debugger = trigger_gemini_debugger

@app.route('/api/strategy_list')
def api_strategy_list():
    try:
        import importlib
        sys.path.insert(0, ROOT_DIR)
        import strategy_backtest.settings as _sb_settings
        importlib.reload(_sb_settings)
        STRATEGY_LIBRARY = _sb_settings.STRATEGY_LIBRARY

        # Merge scan grades + sharpe from scan_results.json
        scan_lookup = {}
        scan_path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner',
                                 'data', 'scan_results.json')
        if os.path.exists(scan_path):
            try:
                with open(scan_path) as f:
                    scan_data = json.load(f)
                for r in scan_data.get('results', []):
                    scan_lookup[str(r['id'])] = {
                        'grade':        r.get('grade'),
                        'sharpe':       r.get('sharpe'),
                        'total_return': r.get('total_return'),
                        'max_drawdown': r.get('max_drawdown'),
                        'total_trades': r.get('total_trades'),
                        'profit_factor':r.get('profit_factor'),
                    }
            except Exception:
                pass

        result = []
        def _sort_key(item):
            k = item[0]
            try:
                return (0, int(k))
            except ValueError:
                try:
                    return (0, int(k.split('_')[0]))
                except ValueError:
                    return (1, k)
        for sid, cfg in sorted(STRATEGY_LIBRARY.items(), key=_sort_key):
            scan = scan_lookup.get(sid, {})
            result.append({
                'sid':        sid,
                'id':         cfg['id'],
                'desc':       cfg['desc'],
                'class':      cfg['class'],
                'coin':       cfg['data']['coins'],
                'timeframe':  cfg['data']['timeframes'],
                'date_from':  cfg['data']['date_from'],
                'date_to':    cfg['data']['date_to'],
                'init_bal':   cfg['risk']['initial_balance'],
                'grade':         scan.get('grade'),
                'sharpe':        scan.get('sharpe'),
                'total_return':  scan.get('total_return'),
                'max_drawdown':  scan.get('max_drawdown'),
                'total_trades':  scan.get('total_trades'),
                'profit_factor': scan.get('profit_factor'),
            })
        return jsonify(result)
    except Exception as e:
        trigger_gemini_debugger(str(e))
        return jsonify({'error': str(e)}), 500


_reload_lock = threading.Lock()

@app.route('/api/strategy_backtest', methods=['POST', 'OPTIONS'])
def api_strategy_backtest():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.json or {}
    strategy_ids = [str(s) for s in data.get('strategy_ids', [])]
    
    # Robust date parsing
    def _safe_date(d, default):
        try:
            if not d or str(d).lower() == 'invalid-date':
                return default
            pd.Timestamp(d)
            return str(d)
        except Exception:
            return default

    date_from = _safe_date(data.get('date_from'), '2021-01-01')
    date_to   = _safe_date(data.get('date_to'),   '2026-05-31')

    if not strategy_ids:
        return jsonify({'error': 'No strategy IDs provided'}), 400

    try:
        import importlib
        sys.path.insert(0, ROOT_DIR)
        from strategy_backtest.engine       import BacktestEngine
        from strategy_backtest.risk         import RiskManager
        from strategy_backtest.metrics      import compute_metrics, _extract_numeric
        from strategy_backtest.run_backtest import load_data
        
        with _reload_lock:
            import strategy_backtest.settings as _sb_settings
            importlib.reload(_sb_settings)
            STRATEGY_LIBRARY = _sb_settings.STRATEGY_LIBRARY

            import strategy_backtest.library as _sb_library
            importlib.reload(_sb_library)

            # Deep-reload forge signal modules so edits to exit/filter/entry signals
            # are picked up without restarting the server.
            for _mod_name in (
                'strategy_forge.indicators',
                'strategy_forge.signals.entry_signals',
                'strategy_forge.signals.filter_signals',
                'strategy_forge.signals.exit_signals',
                'strategy_forge.composer.dna',
                'strategy_forge.strategies',
            ):
                if _mod_name in sys.modules:
                    try:
                        importlib.reload(sys.modules[_mod_name])
                    except Exception:
                        pass

            import strategy_backtest.strategies as strat_reg
            importlib.reload(strat_reg)  # re-reads all strategy files from disk on every call

        results = []
        for sid in strategy_ids:
            if sid not in STRATEGY_LIBRARY:
                continue
            cfg = STRATEGY_LIBRARY[sid]
            try:
                is_multi_coin = isinstance(cfg['data']['coins'], list) and len(cfg['data']['coins']) > 1

                df = load_data(cfg['data']['coins'], cfg['data']['timeframes'], date_from, date_to)

                if isinstance(df, dict):
                    if not df or all(d.empty for d in df.values()):
                        continue
                    if len(next(iter(df.values()))) < 50:
                        continue
                else:
                    if df.empty or len(df) < 50:
                        continue

                strat_cls = getattr(strat_reg, cfg['class'], None)
                if strat_cls is None:
                    continue

                rm = RiskManager(
                    risk_per_trade=cfg['risk']['risk_per_trade'],
                    leverage=cfg['risk']['leverage'],
                    trading_fee=cfg['risk']['trading_fee'],
                    maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
                )

                if is_multi_coin:
                    from strategy_backtest.portfolio_engine import PortfolioBacktestEngine
                    strategy = strat_cls(df, **cfg.get('params', {}))
                    engine = PortfolioBacktestEngine(df, strategy, rm,
                                                    initial_balance=cfg['risk']['initial_balance'])
                else:
                    engine = BacktestEngine(
                        df, strat_cls(df, **cfg.get('params', {})), rm,
                        initial_balance=cfg['risk']['initial_balance']
                    )

                equity = engine.run()
                if not equity or len(equity) < 2:
                    continue

                # Timestamps and price series for display
                if is_multi_coin:
                    idx          = engine._times
                    first_sym    = engine.symbols[0]
                    close_series = engine.dfs[first_sym]['Close'].reindex(idx).ffill()
                else:
                    idx          = engine.df.index
                    close_series = engine.df['Close']

                metrics_raw = compute_metrics(
                    equity, cfg['risk']['initial_balance'],
                    timestamps=idx, trades=engine.trades
                )
                metrics_num = _extract_numeric(metrics_raw)

                init_bal   = float(cfg['risk']['initial_balance'])
                cumret     = [round(v / init_bal - 1, 6) for v in equity]
                n_pts      = len(cumret)
                ts_raw     = [str(t) for t in idx[:n_pts]]
                prices_raw = [round(float(v), 2) if pd.notna(v) else 0.0
                              for v in close_series.values[:n_pts]]

                # Downsample all series with the same indices
                max_pts = 3000
                if n_pts > max_pts:
                    step   = max(1, n_pts // max_pts)
                    ds_idx = list(range(0, n_pts, step))
                    ts_ds     = [ts_raw[i]     for i in ds_idx]
                    cr_ds     = [cumret[i]     for i in ds_idx]
                    prices_ds = [prices_raw[i] for i in ds_idx]
                else:
                    ds_idx    = None
                    ts_ds, cr_ds, prices_ds = ts_raw, cumret, prices_raw

                # Per-coin price series for the Entry/Exit chart
                single_coin = (cfg['data']['coins'] if isinstance(cfg['data']['coins'], str)
                               else cfg['data']['coins'][0])
                if is_multi_coin:
                    prices_by_coin_ds = {}
                    for sym_k in engine.symbols:
                        cs_k = engine.dfs[sym_k]['Close'].reindex(idx).ffill()
                        raw_k = [round(float(v), 2) if pd.notna(v) else 0.0
                                 for v in cs_k.values[:n_pts]]
                        prices_by_coin_ds[sym_k] = (
                            [raw_k[i] for i in ds_idx] if ds_idx else raw_k
                        )
                else:
                    prices_by_coin_ds = {single_coin: prices_ds}

                # Periodic returns
                periodic = {'monthly': {'labels': [], 'values': []},
                            'yearly':  {'labels': [], 'values': []}}
                if 'MONTHLY_RETURNS' in metrics_raw:
                    mdata = metrics_raw['MONTHLY_RETURNS']
                    periodic['monthly'] = {
                        'labels': list(mdata.keys()),
                        'values': [float(v['return'].replace('%', '').replace('+', ''))
                                   for v in mdata.values()]
                    }
                if 'YEARLY_RETURNS' in metrics_raw:
                    ydata = metrics_raw['YEARLY_RETURNS']
                    periodic['yearly'] = {
                        'labels': list(ydata.keys()),
                        'values': [float(v['return'].replace('%', '').replace('+', ''))
                                   for v in ydata.values()]
                    }

                # Round-trip trades — per-symbol stacks to handle multi-coin correctly
                round_trips   = []
                entry_stacks  = {}  # symbol → [entry trade dicts]
                for t in (engine.trades or []):
                    sym = t.get('symbol', '')
                    if t['type'] in ('BUY', 'SELL', 'BUY_ADD', 'SELL_ADD'):
                        entry_stacks.setdefault(sym, []).append(t)
                    elif t['type'] in ('EXIT_LONG', 'EXIT_SHORT'):
                        stack = entry_stacks.get(sym, [])
                        if not stack:
                            continue
                        is_long = t['type'] == 'EXIT_LONG'

                        # Weighted average entry price across all layers
                        total_qty = sum(float(e.get('qty', 0)) for e in stack)
                        if total_qty > 0:
                            avg_ep = sum(float(e.get('qty', 0)) * float(e.get('price', 0))
                                         for e in stack) / total_qty
                        else:
                            avg_ep = float(stack[0].get('price', 0))

                        total_entry_fee      = sum(float(e.get('fee', 0))          for e in stack)
                        total_entry_slippage = sum(float(e.get('slippage_usd', 0)) for e in stack)
                        total_margin         = sum(float(e.get('margin', 0))       for e in stack)
                        total_notional       = sum(float(e.get('notional', 0))     for e in stack)
                        first_entry          = stack[0]

                        exit_fee      = float(t.get('fee', 0))
                        exit_slippage = float(t.get('slippage_usd', 0))
                        gross_pnl     = float(t.get('gross_pnl', 0))
                        total_fees    = total_entry_fee + exit_fee
                        total_slippage = total_entry_slippage + exit_slippage
                        trade_net     = gross_pnl - total_fees

                        xp      = float(t.get('price', 0))
                        ep      = avg_ep
                        roe_pct = round(trade_net / total_margin * 100, 2) if total_margin > 0 else 0.0
                        mkt_pct = round((xp / ep - 1) * 100 if ep > 0 else 0, 2)
                        if not is_long:
                            mkt_pct = round((ep / xp - 1) * 100 if xp > 0 else 0, 2)
                        try:
                            dur = (t['time'] - first_entry['time']).days
                        except Exception:
                            dur = 0
                        round_trips.append({
                            'coin':          sym if sym else single_coin,
                            'entry_time':    str(first_entry['time']),
                            'exit_time':     str(t['time']),
                            'side':          'LONG' if is_long else 'SHORT',
                            'qty':           round(total_qty, 6),
                            'entry_price':   round(ep, 4),
                            'exit_price':    round(xp, 4),
                            'gross_pnl':     round(gross_pnl, 2),
                            'total_fees':    round(total_fees, 2),
                            'slippage_usd':  round(total_slippage, 4),
                            'slippage_pct':  float(t.get('slippage_pct', 0)),
                            'net_profit':    round(trade_net, 2),
                            'mkt_pct':       mkt_pct,
                            'duration_days': dur,
                            'margin':        round(total_margin, 2),
                            'notional':      round(total_notional, 2),
                            'leverage':      int(first_entry.get('leverage', 0)),
                            'reason':        str(t.get('reason', '—')),
                            'roe_pct':       roe_pct,
                            'balance_after': round(float(t.get('balance_after', 0)), 2),
                        })
                        entry_stacks[sym] = []

                # Formatted scalar metrics (exclude MONTHLY/YEARLY dicts)
                fmt_metrics = {}
                for k, v in metrics_raw.items():
                    if k.startswith('MONTHLY') or k.startswith('YEARLY'):
                        continue
                    if isinstance(v, dict):
                        fmt_metrics[k] = v  # keep as dict for JSON serialization (e.g. Regime MDD)
                    else:
                        fmt_metrics[k] = str(v)

                coin_display = ('+'.join(cfg['data']['coins'])
                               if isinstance(cfg['data']['coins'], list)
                               else cfg['data']['coins'])
                results.append({
                    'sid':              sid,
                    'id':               cfg['id'],
                    'class':            cfg['class'],
                    'desc':             cfg['desc'],
                    'coin':             coin_display,
                    'price_coin':       (first_sym if is_multi_coin else cfg['data']['coins']),
                    'timeframe':        cfg['data']['timeframes'],
                    'initial_balance':  init_bal,
                    'leverage':         cfg['risk'].get('leverage', 1),
                    'equity_times':          ts_ds,
                    'equity_cumret':         cr_ds,
                    'equity_prices':         prices_ds,
                    'equity_prices_by_coin': prices_by_coin_ds,
                    'metrics':          metrics_num,
                    'fmt_metrics':      fmt_metrics,
                    'periodic':         periodic,
                    'round_trips':      round_trips,
                })
                print(f"  ✓ {cfg['id']:<45}  Sharpe={metrics_num['Sharpe Ratio']:>6.2f}  "
                      f"Return={metrics_num['Total Return']:>7.1f}%")

            except Exception as e:
                import traceback as _tb
                err_msg = f"Strategy {sid} failed: {e}"
                print(f"  [WARN] {err_msg}")
                _tb.print_exc()
                trigger_gemini_debugger(err_msg)

        return jsonify({'results': results})

    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        trigger_gemini_debugger(str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent_console')
def api_agent_console():
    # 1. Heartbeats from all agents — explicit paths (no crypto- prefix assumption)
    agent_hb_paths = {
        'fullstack':       os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-fullstack',      'heartbeat.json'),
        'researcher':      os.path.join(ROOT_DIR, '.gemini', 'skills', 'alpha-researcher',      'heartbeat.json'),
        'developer':       os.path.join(ROOT_DIR, '.gemini', 'skills', 'alpha-developer',       'heartbeat.json'),
        'data-engineer':   os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-data-engineer',  'heartbeat.json'),
        'strategy-tuner':  os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'heartbeat.json'),
        'qa-tester':       os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-qa-tester',      'heartbeat.json'),
    }
    # fullstack also writes to agent_status.json — prefer that if it exists
    alt_fullstack = os.path.join(ROOT_DIR, 'main_controller', 'agent_status.json')
    if os.path.exists(alt_fullstack):
        agent_hb_paths['fullstack'] = alt_fullstack

    statuses = {}
    for agent, path in agent_hb_paths.items():
        if os.path.exists(path):
            try:
                with open(path) as f:
                    statuses[agent] = json.load(f)
            except Exception:
                statuses[agent] = {"status": "ERROR", "detail": "Corrupt heartbeat"}
        else:
            statuses[agent] = {"status": "OFFLINE", "ts": None, "detail": "No heartbeat found"}

    # 2. Fix History (last 10 entries from AGENT_COLLABORATION.md)
    collab_path = os.path.join(ROOT_DIR, '.gemini', 'shared', 'AGENT_COLLABORATION.md')
    history = []
    if os.path.exists(collab_path):
        try:
            with open(collab_path) as f:
                lines = [l.strip() for l in f if l.strip() and '|' in l]
                # Filter out headers and take last 10
                content_lines = [l for l in lines if not l.startswith('| Date') and not l.startswith('|---')]
                history = content_lines[-10:]
        except Exception:
            pass

    # 3. System Health (from Data Engineer)
    health_path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-data-engineer', 'logs', 'system_health.log')
    health_summary = "No health log found."
    if os.path.exists(health_path):
        try:
            with open(health_path) as f:
                # Get last 20 lines of health log
                lines = f.readlines()
                health_summary = "".join(lines[-20:])
        except Exception:
            pass

    return jsonify({
        'statuses': statuses,
        'history':  history,
        'health':   health_summary
    })

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(CONTROLLER_DIR, path)):
        resp = send_from_directory(CONTROLLER_DIR, path)
    elif os.path.exists(os.path.join(ROOT_DIR, 'phase_6_agent_monitor', path)):
        resp = send_from_directory(os.path.join(ROOT_DIR, 'phase_6_agent_monitor'), path)
    else:
        resp = send_from_directory(ROOT_DIR, path)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/agent_monitor')
def agent_monitor():
    return send_from_directory(os.path.join(ROOT_DIR, 'phase_6_agent_monitor'), 'index.html')

@app.route('/api/trigger_agent_action', methods=['POST'])
def api_trigger_agent_action():
    data = request.json or {}
    action = data.get('action') # 'REPAIR' or 'RESEARCH'
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    now_ts = datetime.now().isoformat()

    if action == 'REPAIR':
        target_inbox = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-data-engineer', 'inbox')
        payload = {
            'from': 'System_UI', 'priority': 'HIGH', 'topic': 'MANUAL_REPAIR_TRIGGER',
            'message': 'User triggered manual system-wide data repair and scan.',
            'ts': now_ts
        }
    elif action == 'RESEARCH':
        target_inbox = os.path.join(ROOT_DIR, '.gemini', 'skills', 'alpha-researcher', 'inbox')
        payload = {
            'from': 'System_UI', 'priority': 'HIGH', 'topic': 'MANUAL_RESEARCH_TRIGGER',
            'message': 'User triggered manual alpha-hunting research cycle.',
            'ts': now_ts
        }
    elif action == 'KILL_ALL':
        # Kill all running agent watchers
        killed = []
        pids = load_watcher_pids()
        for agent_id, pid in list(pids.items()):
            try:
                os.kill(int(pid), signal.SIGTERM)
                killed.append(agent_id)
            except Exception:
                pass
        pids.clear()
        save_watcher_pids(pids)
        # pgrep sweep for any orphans
        try:
            orphans = subprocess.check_output(['pgrep', '-f', 'agent_watcher.py']).decode().split()
            for opid in orphans:
                try: os.kill(int(opid), signal.SIGTERM)
                except: pass
        except: pass
        # Write OFFLINE heartbeats
        for agent_name in ['crypto-fullstack', 'crypto-data-engineer', 'alpha-researcher', 'alpha-developer', 'crypto-strategy-tuner', 'crypto-qa-tester']:
            hb_path = os.path.join(ROOT_DIR, '.gemini', 'skills', agent_name, 'heartbeat.json')
            try:
                with open(hb_path, 'w') as f:
                    json.dump({'ts': now_ts, 'status': 'OFFLINE', 'action': 'Terminated by user'}, f, indent=2)
            except: pass
        return jsonify({'message': f'All agents terminated. Killed: {killed or "none tracked"}'})
    else:
        return jsonify({'error': 'Unknown action'}), 400

    try:
        os.makedirs(target_inbox, exist_ok=True)
        filename = f"{ts}_manual_{action}.json"
        with open(os.path.join(target_inbox, filename), 'w') as f:
            json.dump(payload, f, indent=2)
        return jsonify({'message': f'Action {action} dispatched to agent inbox.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _write_tuner_inbox(topic, instruction, priority='HIGH'):
    """Write an inbox message to the strategy tuner and ensure its watcher is alive."""
    inbox_dir = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'inbox')
    os.makedirs(inbox_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    payload = {
        'topic':       topic,
        'from':        'dashboard',
        'priority':    priority,
        'instruction': instruction,
        'ts':          datetime.now().isoformat(),
    }
    with open(os.path.join(inbox_dir, f'{ts}_from_dashboard_{topic}.json'), 'w') as f:
        json.dump(payload, f, indent=2)

    # Ensure the tuner watcher is running so it picks up the message within 30s
    try:
        orphans = subprocess.check_output(['pgrep', '-f', f'agent_watcher.py tuner']).decode().split()
    except:
        orphans = []
    
    is_alive = len(orphans) > 0
    if not is_alive:
        standby_flag = os.path.join(ROOT_DIR, '.gemini', 'skills',
                                    'crypto-strategy-tuner', 'standby_mode.flag')
        try: os.remove(standby_flag)
        except: pass
        proc = subprocess.Popen(
            [VENV_PYTHON, _WATCHER_SCRIPT, 'tuner'],
            cwd=ROOT_DIR, start_new_session=True)
        # Update PIDs file for dashboard consistency
        pids = load_watcher_pids()
        pids['tuner'] = proc.pid
        save_watcher_pids(pids)


@app.route('/api/run_tuner_scan', methods=['POST'])
def api_run_tuner_scan():
    """RUN SCAN — write force_rescan.flag + inbox message so tuner scans within 30s."""
    flag_path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner',
                             'data', 'force_rescan.flag')
    os.makedirs(os.path.dirname(flag_path), exist_ok=True)
    try:
        open(flag_path, 'w').close()
        _write_tuner_inbox(
            topic='RUN_SCAN_NOW',
            instruction=(
                'The user clicked RUN SCAN from the dashboard. '
                'Ignore the scan-skip logic. Run scan_all.py immediately regardless '
                'of classified state. force_rescan.flag has been written for you.'
            ),
        )
        return jsonify({'message': 'Scan triggered — tuner will start within 30s.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scan_new_strategies', methods=['POST'])
def api_scan_new_strategies():
    """SCAN NEW — runs scan_all.py --new-only directly (no Gemini agent, zero quota)."""
    scan_script = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'scripts', 'scan_all.py')
    scan_results_path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'data', 'scan_results.json')

    # Count how many new strategies exist before running
    try:
        from strategy_backtest.settings import STRATEGY_LIBRARY
        existing_ids = set()
        if os.path.exists(scan_results_path):
            with open(scan_results_path) as f:
                existing_ids = {str(r['id']) for r in json.load(f).get('results', [])}
        new_ids = [sid for sid in STRATEGY_LIBRARY if sid not in existing_ids]
        if not new_ids:
            return jsonify({'message': 'No new strategies found — scan_results.json is already up to date.', 'new_count': 0})
    except Exception as e:
        return jsonify({'error': f'Could not check strategy list: {e}'}), 500

    try:
        subprocess.Popen(
            [VENV_PYTHON, scan_script, '--new-only'],
            cwd=ROOT_DIR,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({
            'message': f'Scanning {len(new_ids)} new strategies (IDs: {", ".join(new_ids)}) — no quota used.',
            'new_count': len(new_ids),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/grade_pending', methods=['POST'])
def api_grade_pending():
    """GRADE PENDING — tells the tuner agent to classify PENDING strategies only, no rescan."""
    scan_results_path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner',
                                     'data', 'scan_results.json')
    try:
        pending = []
        if os.path.exists(scan_results_path):
            with open(scan_results_path) as f:
                data = json.load(f)
            pending = [r['id'] for r in data.get('results', []) if r.get('grade') == 'PENDING']

        if not pending:
            return jsonify({'message': 'No PENDING strategies found — nothing to grade.', 'pending_count': 0})

        _write_tuner_inbox(
            topic='GRADE_PENDING_NOW',
            instruction=(
                f'There are {len(pending)} strategies with grade PENDING (IDs: {", ".join(str(p) for p in pending)}). '
                'Do NOT run scan_all.py. Do NOT rescan anything. '
                'Open scan_results.json, find every entry with grade "PENDING", '
                'classify each one as GOOD / MEDIOCRE / BAD using your grading criteria, '
                'write grade_reason for each, then set classified: true and update the grade counts. '
                'Only touch PENDING entries — leave all existing grades untouched.'
            ),
        )
        return jsonify({
            'message': f'Grading {len(pending)} PENDING strategies (IDs: {", ".join(str(p) for p in pending)}) — tuner will start within 30s.',
            'pending_count': len(pending),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trigger_tuner_rescan', methods=['POST'])
def api_trigger_tuner_rescan():
    """FORCE RESCAN — write force_rescan.flag + inbox message for immediate pickup."""
    flag_path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner',
                             'data', 'force_rescan.flag')
    os.makedirs(os.path.dirname(flag_path), exist_ok=True)
    try:
        open(flag_path, 'w').close()
        _write_tuner_inbox(
            topic='FORCE_RESCAN_NOW',
            instruction=(
                'The user clicked FORCE RESCAN from the dashboard. '
                'Delete scan_results.json, then run scan_all.py for a completely '
                'fresh scan. Classify all results afterwards. '
                'force_rescan.flag has been written for you.'
            ),
        )
        return jsonify({'message': 'Force rescan triggered — tuner will start within 30s.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/strategy_scan_results')
def api_strategy_scan_results():
    """Return latest scan_results.json from the strategy tuner agent."""
    path = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'data', 'scan_results.json')
    if not os.path.exists(path):
        return jsonify({'results': [], 'scanned_at': None, 'total': 0})
    try:
        with open(path) as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate_strategy', methods=['GET', 'OPTIONS'])
def api_validate_strategy():
    """Run rulebook validation for a single strategy (quick mode by default)."""
    if request.method == 'OPTIONS':
        return '', 204
    strategy_id = str(request.args.get('strategy_id', '')).strip()
    quick = request.args.get('quick', 'true').lower() != 'false'
    if not strategy_id:
        return jsonify({'error': 'strategy_id required'}), 400
    try:
        import importlib
        sys.path.insert(0, ROOT_DIR)
        import strategy_backtest.library as _sb_library
        importlib.reload(_sb_library)
        import strategy_backtest.strategies as strat_reg
        importlib.reload(strat_reg)
        import strategy_backtest.validator as _val
        importlib.reload(_val)
        result = _val.validate(strategy_id, n_folds=4, quick=quick)
        if not result:
            return jsonify({'error': f'Strategy {strategy_id} not found or failed'}), 400
        return jsonify(result)
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/trigger_finetune', methods=['POST'])
def api_trigger_finetune():
    """Write a FINETUNE inbox message to the strategy tuner agent."""
    data        = request.json or {}
    strategy_id = str(data.get('strategy_id', ''))
    # n_trials intentionally omitted from payload — finetune.py auto-scales
    # based on number of tunable params (max(100, n_tunable × 25))

    if not strategy_id:
        return jsonify({'error': 'strategy_id required'}), 400

    inbox_dir = os.path.join(ROOT_DIR, '.gemini', 'skills', 'crypto-strategy-tuner', 'inbox')
    os.makedirs(inbox_dir, exist_ok=True)
    ts      = datetime.now().strftime('%Y%m%d_%H%M%S')
    payload = {
        'from':        'System_UI',
        'priority':    'HIGH',
        'topic':       'FINETUNE',
        'strategy_id': strategy_id,
        'message':     f'User requested fine-tuning for strategy ID {strategy_id} (auto-scaled trials)',
        'ts':          datetime.now().isoformat(),
    }
    try:
        with open(os.path.join(inbox_dir, f'{ts}_finetune_{strategy_id}.json'), 'w') as f:
            json.dump(payload, f, indent=2)
        return jsonify({'message': f'Fine-tune request for strategy {strategy_id} queued.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Phase 7 mining API ────────────────────────────────────────────────────────
_p7 = {
    'proc':       None,   # active Popen instance
    'logs':       [],     # rolling stdout lines (capped at 300)
    'is_running': False,
    'last_run':   None,   # ISO timestamp of last completed run
}

def _p7_stdout_reader(proc):
    """Background thread: drain miner stdout into _p7['logs'] and clear is_running when done."""
    for raw in iter(proc.stdout.readline, b''):
        line = raw.decode('utf-8', errors='replace').rstrip()
        _p7['logs'].append(line)
        if len(_p7['logs']) > 300:
            _p7['logs'] = _p7['logs'][-200:]
    proc.wait()
    _p7['is_running'] = False
    _p7['last_run']   = datetime.now().isoformat()


@app.route('/api/phase_7/trigger_mining', methods=['POST', 'OPTIONS'])
def api_p7_trigger_mining():
    if request.method == 'OPTIONS':
        return '', 204

    if _p7['is_running']:
        return jsonify({'error': 'Mining already running — wait for it to finish or reload.'}), 409

    data        = request.json or {}
    strategy_id = str(data.get('strategy_id', '')).strip()
    trials      = data.get('trials')
    no_resume   = bool(data.get('no_resume', False))

    if not strategy_id:
        return jsonify({'error': 'strategy_id is required'}), 400

    miner_script = os.path.join(ROOT_DIR, 'phase_7', 'miner.py')
    cmd = [VENV_PYTHON, miner_script, '--strategy_id', strategy_id]
    if trials:
        cmd += ['--trials', str(int(trials))]
    if no_resume:
        cmd += ['--no_resume']

    try:
        _p7['logs']       = []
        _p7['is_running'] = True
        _p7['proc']       = subprocess.Popen(
            cmd, cwd=ROOT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1,
        )
        t = threading.Thread(target=_p7_stdout_reader, args=(_p7['proc'],), daemon=True)
        t.start()
        return jsonify({'message': f'Mining started for strategy {strategy_id}'})
    except Exception as e:
        _p7['is_running'] = False
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_7/status')
def api_p7_status():
    # Also check process exit in case thread hasn't updated yet
    if _p7['proc'] is not None and _p7['is_running']:
        if _p7['proc'].poll() is not None:
            _p7['is_running'] = False
            _p7['last_run']   = datetime.now().isoformat()
    return jsonify({
        'is_running': _p7['is_running'],
        'last_logs':  list(_p7['logs']),
        'status':     {'last_run': _p7['last_run']},
    })


@app.route('/api/phase_7/stop_mining', methods=['POST', 'OPTIONS'])
def api_p7_stop_mining():
    if request.method == 'OPTIONS':
        return '', 204
    proc = _p7.get('proc')
    if proc is None or not _p7['is_running']:
        return jsonify({'message': 'No mining process is running.'}), 200
    try:
        proc.terminate()
        _p7['is_running'] = False
        _p7['logs'].append('[STOPPED] Mining was terminated by user.')
        return jsonify({'message': 'Mining process terminated.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_7/run_tuner', methods=['POST', 'OPTIONS'])
def api_p7_run_tuner():
    if request.method == 'OPTIONS':
        return '', 204
    if _p7['is_running']:
        return jsonify({'error': 'Another Phase 7 process is already running.'}), 409
    data        = request.json or {}
    strategy_id = str(data.get('strategy_id', '')).strip()
    if not strategy_id:
        return jsonify({'error': 'strategy_id is required'}), 400
    probe_trials = data.get('probe_trials', 30)
    max_iter     = data.get('max_iter', 5)
    run_miner    = bool(data.get('run_miner', False))
    tuner_script = os.path.join(ROOT_DIR, 'phase_7', 'agents', 'tuner_agent.py')
    if not os.path.exists(tuner_script):
        return jsonify({'error': 'tuner_agent.py not found.'}), 404
    cmd = [VENV_PYTHON, tuner_script,
           '--strategy_id', strategy_id,
           '--probe_trials', str(int(probe_trials)),
           '--max_iter',     str(int(max_iter))]
    if run_miner:
        cmd.append('--run_miner')
    try:
        _p7['logs'] = []
        _p7['is_running'] = True
        _p7['proc'] = subprocess.Popen(
            cmd, cwd=ROOT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1,
        )
        t = threading.Thread(target=_p7_stdout_reader, args=(_p7['proc'],), daemon=True)
        t.start()
        return jsonify({'message': f'Tuner agent started for strategy {strategy_id}'})
    except Exception as e:
        _p7['is_running'] = False
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_7/patch_results', methods=['POST', 'OPTIONS'])
def api_p7_patch_results():
    if request.method == 'OPTIONS':
        return '', 204
    if _p7['is_running']:
        return jsonify({'error': 'Cannot patch while mining is running.'}), 409
    patch_script = os.path.join(ROOT_DIR, 'phase_7', 'scripts', 'patch_metrics.py')
    if not os.path.exists(patch_script):
        return jsonify({'error': 'patch_metrics.py not found.'}), 404
    try:
        _p7['logs'] = []
        _p7['is_running'] = True
        _p7['proc'] = subprocess.Popen(
            [VENV_PYTHON, patch_script], cwd=ROOT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1,
        )
        t = threading.Thread(target=_p7_stdout_reader, args=(_p7['proc'],), daemon=True)
        t.start()
        return jsonify({'message': 'Patch started — watch the Mining Monitor for progress.'})
    except Exception as e:
        _p7['is_running'] = False
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_7/compound/<strategy_id>', methods=['GET', 'OPTIONS'])
def api_p7_compound(strategy_id):
    if request.method == 'OPTIONS':
        return '', 204
    import csv as _csv
    from collections import defaultdict
    start_capital = float(request.args.get('capital', 1000))
    csv_path = os.path.join(ROOT_DIR, 'phase_7', 'data', 'wisdom_matrix.csv')
    try:
        rows = []
        with open(csv_path) as f:
            for r in _csv.DictReader(f):
                if r.get('strategy_id') == str(strategy_id):
                    rows.append(r)
    except FileNotFoundError:
        return jsonify({'error': 'wisdom_matrix.csv not found'}), 404

    if not rows:
        return jsonify({'error': f'No data for strategy {strategy_id}'}), 404

    by_type = defaultdict(list)
    for r in rows:
        by_type[r['window_type']].append(r)

    TYPE_ORDER = ['1M','2M','3M','4M','6M','1Y','2Y','3Y']
    result = {}
    for wtype in TYPE_ORDER:
        if wtype not in by_type:
            continue
        sorted_rows = sorted(by_type[wtype], key=lambda r: r['start_date'])
        # Drop overlapping windows — keep only non-overlapping sequential periods
        wrows = []
        last_end = None
        for r in sorted_rows:
            if last_end is None or r['start_date'] >= last_end:
                wrows.append(r)
                last_end = r.get('end_date', '')
        capital = start_capital
        peak    = capital
        max_dd  = 0.0
        chain   = []
        for r in wrows:
            roi         = float(r['roi']) / 100
            end_capital = capital * (1 + roi)
            peak        = max(peak, end_capital)
            dd          = (peak - end_capital) / peak * 100 if peak > 0 else 0
            max_dd      = max(max_dd, dd)
            chain.append({
                'start_date':    r['start_date'],
                'end_date':      r.get('end_date', ''),
                'regime':        r['regime'],
                'window_roi':    round(float(r['roi']), 2),
                'sharpe':        round(float(r['sharpe']), 3),
                'start_capital': round(capital, 2),
                'end_capital':   round(end_capital, 2),
            })
            capital = end_capital
        result[wtype] = {
            'chain':         chain,
            'final_capital': round(capital, 2),
            'total_roi':     round((capital - start_capital) / start_capital * 100, 2),
            'max_drawdown':  round(max_dd, 2),
            'windows':       len(wrows),
        }

    return jsonify({'strategy_id': strategy_id, 'start_capital': start_capital, 'chains': result})


@app.route('/api/phase_7/agent_log', methods=['GET', 'OPTIONS'])
def api_p7_agent_log():
    if request.method == 'OPTIONS':
        return '', 204
    ltm_path = os.path.join(ROOT_DIR, 'phase_7', 'agents', 'LTM.md')
    try:
        with open(ltm_path) as f:
            content = f.read()
    except FileNotFoundError:
        content = '## Adjustment Log\n\n_No runs yet._'
    return jsonify({'content': content, 'live_logs': list(_p7['logs']), 'is_running': _p7['is_running']})


# ── Phase 10 Pairs Trading API ────────────────────────────────────────────────
_p10 = {
    'proc':       None,
    'logs':       [],
    'is_running': False,
    'last_run':   None,
}

def _p10_stdout_reader(proc):
    for raw in iter(proc.stdout.readline, b''):
        line = raw.decode('utf-8', errors='replace').rstrip()
        _p10['logs'].append(line)
        if len(_p10['logs']) > 300:
            _p10['logs'] = _p10['logs'][-200:]
    proc.wait()
    _p10['is_running'] = False
    _p10['last_run'] = datetime.now().isoformat()


# ── Phase 11 Crossover Strategy API ──────────────────────────────────────────
_p11 = {
    'proc':       None,
    'logs':       [],
    'is_running': False,
    'last_run':   None,
}

def _p11_stdout_reader(proc):
    for raw in iter(proc.stdout.readline, b''):
        line = raw.decode('utf-8', errors='replace').rstrip()
        _p11['logs'].append(line)
        if len(_p11['logs']) > 300:
            _p11['logs'] = _p11['logs'][-200:]
    proc.wait()
    _p11['is_running'] = False
    _p11['last_run'] = datetime.now().isoformat()


@app.route('/api/phase_10/run_backtest', methods=['POST', 'OPTIONS'])
def api_p10_run_backtest():
    if request.method == 'OPTIONS':
        return '', 204
    if _p10['is_running']:
        return jsonify({'error': 'Backtest already running.'}), 409
    data      = request.json or {}
    pair      = data.get('pair', '')
    date_from = data.get('date_from', '2023-01-01')
    date_to   = data.get('date_to',   '2026-05-31')
    timeframe = data.get('timeframe', '1h')
    signal_tf = data.get('signal_timeframe', '')
    mode      = data.get('mode', 'advanced')
    script    = os.path.join(ROOT_DIR, 'phase_10', 'backtest.py')
    cmd       = [VENV_PYTHON, script, '--date_from', date_from, '--date_to', date_to, '--timeframe', timeframe]
    if signal_tf:
        cmd += ['--signal_timeframe', signal_tf]
    elif timeframe in ('4h', '1d'):
        # Coarser TFs auto-route: signal_tf=chosen TF, execution_tf=1h (handled in backtest.py)
        pass
    if mode:
        cmd += ['--mode', mode]
    if pair:
        cmd += ['--pair', pair]
    try:
        _p10['logs']       = []
        _p10['is_running'] = True
        _p10['proc']       = subprocess.Popen(
            cmd, cwd=ROOT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        t = threading.Thread(target=_p10_stdout_reader, args=(_p10['proc'],), daemon=True)
        t.start()
        return jsonify({'message': 'Phase 10 backtest started.'})
    except Exception as e:
        _p10['is_running'] = False
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_10/status')
def api_p10_status():
    if _p10['proc'] is not None and _p10['is_running']:
        if _p10['proc'].poll() is not None:
            _p10['is_running'] = False
            _p10['last_run'] = datetime.now().isoformat()
    return jsonify({
        'is_running': _p10['is_running'],
        'logs':       list(_p10['logs']),
        'last_run':   _p10['last_run'],
    })


@app.route('/api/phase_10/stop', methods=['POST', 'OPTIONS'])
def api_p10_stop():
    if request.method == 'OPTIONS':
        return '', 204
    proc = _p10.get('proc')
    if proc is None or not _p10['is_running']:
        return jsonify({'message': 'No process running.'}), 200
    try:
        proc.terminate()
        _p10['is_running'] = False
        _p10['logs'].append('[STOPPED] Backtest terminated by user.')
        return jsonify({'message': 'Stopped.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_10/results')
def api_p10_results():
    mode = request.args.get('mode', 'advanced')
    tf   = request.args.get('tf', '1h')
    # Normalise mode to advanced|wright
    if mode not in ('advanced', 'wright'):
        mode = 'advanced'
    # Primary: new unified naming results_{mode}_{tf}.json
    filename = f'results_{mode}_{tf}.json'
    results_file = os.path.join(ROOT_DIR, 'phase_10', 'data', filename)
    # Fallback to legacy filenames for backward compat
    if not os.path.exists(results_file):
        if mode == 'wright':
            results_file = os.path.join(ROOT_DIR, 'phase_10', 'data', 'results_wright.json')
        else:
            results_file = os.path.join(ROOT_DIR, 'phase_10', 'data', 'results.json')
    if not os.path.exists(results_file):
        return jsonify({'error': 'No results yet. Run the backtest first.'}), 404
    try:
        with open(results_file) as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_10/available_results')
def api_p10_available_results():
    """Return which (mode, timeframe) result files exist."""
    data_dir = os.path.join(ROOT_DIR, 'phase_10', 'data')
    available = {}
    for mode in ('advanced', 'wright'):
        available[mode] = []
        for tf in ('5m', '15m', '1h', '4h', '1d'):
            f = os.path.join(data_dir, f'results_{mode}_{tf}.json')
            if os.path.exists(f):
                available[mode].append(tf)
        # Legacy fallback
        legacy = 'results_wright.json' if mode == 'wright' else 'results.json'
        if not available[mode] and os.path.exists(os.path.join(data_dir, legacy)):
            available[mode].append('1h')
    return jsonify(available)


@app.route('/api/phase_11/run_backtest', methods=['POST', 'OPTIONS'])
def api_p11_run_backtest():
    if request.method == 'OPTIONS':
        return '', 204
    if _p11['is_running']:
        return jsonify({'error': 'Backtest already running.'}), 409
    data      = request.json or {}
    pair      = data.get('pair', '')
    date_from = data.get('date_from', '2023-01-01')
    date_to   = data.get('date_to',   '2026-05-31')
    timeframe = data.get('timeframe', '1h')
    script    = os.path.join(ROOT_DIR, 'phase_11', 'backtest.py')
    cmd       = [VENV_PYTHON, script, '--date_from', date_from, '--date_to', date_to, '--timeframe', timeframe]
    if pair:
        cmd += ['--pair', pair]
    try:
        _p11['logs']       = []
        _p11['is_running'] = True
        _p11['proc']       = subprocess.Popen(
            cmd, cwd=ROOT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        t = threading.Thread(target=_p11_stdout_reader, args=(_p11['proc'],), daemon=True)
        t.start()
        return jsonify({'message': 'Phase 11 backtest started.'})
    except Exception as e:
        _p11['is_running'] = False
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_11/status')
def api_p11_status():
    if _p11['proc'] is not None and _p11['is_running']:
        if _p11['proc'].poll() is not None:
            _p11['is_running'] = False
            _p11['last_run'] = datetime.now().isoformat()
    return jsonify({
        'is_running': _p11['is_running'],
        'logs':       list(_p11['logs']),
        'last_run':   _p11['last_run'],
    })


@app.route('/api/phase_11/stop', methods=['POST', 'OPTIONS'])
def api_p11_stop():
    if request.method == 'OPTIONS':
        return '', 204
    proc = _p11.get('proc')
    if proc is None or not _p11['is_running']:
        return jsonify({'message': 'No process running.'}), 200
    try:
        proc.terminate()
        _p11['is_running'] = False
        _p11['logs'].append('[STOPPED] Backtest terminated by user.')
        return jsonify({'message': 'Stopped.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phase_11/results')
def api_p11_results():
    results_file = os.path.join(ROOT_DIR, 'phase_11', 'data', 'results.json')
    if not os.path.exists(results_file):
        return jsonify({'error': 'No results yet. Run the backtest first.'}), 404
    try:
        with open(results_file) as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _load_openrouter_key():
    key_file = os.path.join(ROOT_DIR, 'API & others', 'open_router_API.txt')
    try:
        with open(key_file) as f:
            return f.read().strip()
    except Exception:
        return ''

_OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
_STRATEGY_FORGE_DOC  = os.path.join(ROOT_DIR, 'docs', 'important', 'strategy_forge_flow.md')
_SETTINGS_FILE       = os.path.join(ROOT_DIR, 'strategy_backtest', 'settings.py')

_STYLE_SCRIPT_MAP = {
    'mft':          'mtf_search.py',
    'hft':          'hft_search.py',
    'swing':        'sniper_swing_search.py',
    'sniper_swing': 'sniper_swing_search.py',
    'alpha':        'alpha_forge_search.py',
    'general':      'random_search.py',
}

def _load_strategy_context():
    try:
        with open(_STRATEGY_FORGE_DOC, encoding='utf-8') as f:
            content = f.read()
    except Exception:
        content = ''

    action_instructions = """

--- ACTION SYSTEM ---
You can take REAL actions in the Crypto-RL project. You have THREE action types below. Choose the right one based on the user's request.

OUTPUT FORMAT — place the action block at the VERY END of your reply:

PRIMARY ACTION — automated strategy search (use this when user asks to "find", "search", "discover" a strategy matching requirements like style/hold time/ROI/Sharpe):
%%ACTION%%
{"type": "run_search", "style": "mft", "coin": "ETH", "tf": "1h", "n": 150, "score": "blend"}
%%END_ACTION%%

STYLE GUIDE — pick the right style from user's requirements:
- mft:     2-7 trades/week, 1h TF, 1-4 day hold, monthly 2-5%, MDD <25%, Sharpe 1+
- hft:     20-100 trades/week, 5m or 15m TF, 5-50 min hold, monthly 5-15%
- swing:   1-3 trades/week, 5m entry + 4h HTF bias, 2-12h hold, Sharpe 1.5+
- alpha:   test new exit methods (trailing_tp, psar_trail, vol_adaptive_sl) and new entries
- general: unconstrained random search, any TF and style

SECONDARY ACTION — only when user specifies EXACT entry signal + exit method to build and finetune:
%%ACTION%%
{"type": "auto_pipeline", "entry": "ENTRY_NAME", "filters": ["filter1"], "exit_method": "EXIT_NAME", "params": {"atr_period": 14, "sl_atr_mult": 2.0}, "coin": "ETH", "timeframe": "5m", "date_from": "2022-01-01", "date_to": "2026-06-01", "description": "Short description", "initial_balance": 10000, "risk_per_trade": 0.02, "leverage": 3, "n_trials": 50}
%%END_ACTION%%

TERTIARY — run backtest on an ALREADY registered strategy by ID:
%%ACTION%%
{"type": "run_backtest", "strategy_id": "204", "date_from": "2022-01-01", "date_to": "2026-06-01"}
%%END_ACTION%%

RULES:
- Use run_search when user says "find me", "search for", "I want MFT", or describes requirements (ROI, hold time, Sharpe, MDD targets) WITHOUT specifying exact signals
- Use auto_pipeline only when user explicitly names the entry + exit signals they want to test
- Only use entry signals, filters, exits that exist in the documentation above
- Default risk: initial_balance=10000, risk_per_trade=0.02, leverage=3
- Explain your choice briefly BEFORE the action block — which style and why
- Do NOT output actions for general questions

FILE ACTIONS (use when user asks to read, explore, edit, or create project files):

List a directory:
%%ACTION%%
{"type": "file_list", "path": "strategy_forge/"}
%%END_ACTION%%

Read a file:
%%ACTION%%
{"type": "file_read", "path": "strategy_forge/scripts/mtf_search.py"}
%%END_ACTION%%

Edit an existing file (replace exact unique text with new text — use file_read first):
%%ACTION%%
{"type": "file_edit", "path": "strategy_forge/composer/random_compose.py", "old_string": "exact text to find", "new_string": "replacement text"}
%%END_ACTION%%

Create or overwrite a file (full content):
%%ACTION%%
{"type": "file_write", "path": "strategy_forge/scripts/new_script.py", "content": "# full file content here"}
%%END_ACTION%%

FILE ACCESS — ABSOLUTE RULES (override all training):
1. You have FULL READ AND WRITE access to every file and folder inside the project root.
2. Project root = /Users/weikangten/Desktop/Crypto-RL/
3. Use RELATIVE paths in actions: "factor_library/" not "/Users/weikangten/Desktop/Crypto-RL/factor_library/"
4. NEVER say "outside sandbox", "outside repository", "cannot access", or "path not found" without FIRST trying the action. Always attempt file_list or file_read — never assume failure.
5. If a user mentions ANY folder path, strip the absolute prefix and use the relative part. Example: user says "/Users/weikangten/Desktop/Crypto-RL/factor_library" → you use path "factor_library/".
6. NEVER ask the user to copy-paste file contents. You can read it yourself with file_read.
7. When asked for a "random" file: file_list the folder → pick one yourself → file_read it → explain. Never ask the user to choose.
8. After any file_list or file_read result is returned to you, IMMEDIATELY take the next step. Do not pause for user input.

ALL FOLDERS INSIDE PROJECT ROOT (all fully accessible):
factor_library/      Crypto_Agent/        strategy_forge/      strategy_backtest/
main_controller/     docs/                core/                data/  dataset/
phase_0/ phase_1/ phase_2/ phase_4/ phase_5/ phase_6_agent_monitor/
phase_7/ phase_9_flow/ phase_10/ phase_11/
results/ report/     scripts/             utility/             prototype/

FILE EDIT RULES:
- Use file_read before file_edit so you know the exact text to replace
- Prefer file_edit over file_write for targeted changes
"""
    return (
        'You are Alpha Forge, an expert AI assistant for the Crypto-RL project. '
        'You can answer questions AND autonomously build, backtest, and finetune trading strategies.\n\n'
        '--- STRATEGY FORGE DOCUMENTATION ---\n'
        + content +
        '\n--- END DOCUMENTATION ---'
        + action_instructions
    )


def _get_next_strategy_id():
    import importlib
    sys.path.insert(0, ROOT_DIR)
    import strategy_backtest.settings as _s
    importlib.reload(_s)
    ids = [int(k) for k in _s.STRATEGY_LIBRARY.keys() if k.isdigit()]
    return max(ids) + 1 if ids else 300


def _build_entry_str(new_id, sid_str, description, coin, timeframe,
                     date_from, date_to, init_bal, risk_pt, leverage, full_params):
    param_lines  = [f'            {repr(k)}: {repr(v)}' for k, v in full_params.items()]
    params_block = '{\n' + ',\n'.join(param_lines) + '\n        }'
    return (
        f'\n    "{new_id}": {{\n'
        f'        "id":    "{sid_str}",\n'
        f'        "desc":  "{description}",\n'
        f'        "class": "ForgeStrategy",\n'
        f'        "data":  {{"coins": "{coin}", "timeframes": "{timeframe}", "date_from": "{date_from}", "date_to": "{date_to}"}},\n'
        f'        "risk":  {{"initial_balance": {init_bal}, "risk_per_trade": {risk_pt}, "leverage": {leverage}, "trading_fee": 0.0004, "maintenance_margin_rate": 0.005}},\n'
        f'        "params": {params_block},\n'
        f'    }},'
    )


def _insert_entry_into_content(content: str, entry_str: str) -> str:
    import re
    m = re.search(r'\n\}(\s*\n# --- Current Active Strategy)', content)
    if not m:
        raise ValueError('Cannot locate STRATEGY_LIBRARY closing brace in settings.py')
    insert_at = m.start() + 1
    return content[:insert_at] + entry_str + '\n' + content[insert_at:]


def _append_to_settings(new_id: int, entry_str: str):
    with open(_SETTINGS_FILE, encoding='utf-8') as f:
        content = f.read()
    with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        f.write(_insert_entry_into_content(content, entry_str))


def _replace_strategy_params(new_id: int, sid_str: str, description: str, coin: str,
                              timeframe: str, date_from: str, date_to: str,
                              init_bal: float, risk_pt: float, leverage: int, full_params: dict):
    """Remove old entry for new_id and re-insert with updated params."""
    with open(_SETTINGS_FILE, encoding='utf-8') as f:
        content = f.read()
    start = content.find(f'\n    "{new_id}": {{')
    if start == -1:
        raise ValueError(f'Strategy {new_id} not found in settings.py')
    end = content.find('\n    },', start + 1) + 7
    content = content[:start] + content[end:]
    new_entry = _build_entry_str(new_id, sid_str, description, coin, timeframe,
                                  date_from, date_to, init_bal, risk_pt, leverage, full_params)
    with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        f.write(_insert_entry_into_content(content, new_entry))




_WATCHER_PIDS_FILE = os.path.join(ROOT_DIR, 'Crypto_Agent', 'active_watchers.json')
_WATCHER_PIDS_FILE = os.path.join(ROOT_DIR, 'Crypto_Agent', 'active_watchers.json')

def load_watcher_pids():
    if os.path.exists(_WATCHER_PIDS_FILE):
        try:
            with open(_WATCHER_PIDS_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def save_watcher_pids(pids):
    try:
        os.makedirs(os.path.dirname(_WATCHER_PIDS_FILE), exist_ok=True)
        with open(_WATCHER_PIDS_FILE, 'w') as f:
            json.dump(pids, f, indent=2)
    except: pass

def is_pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except:
        return False

def cleanup_orphaned_watchers():
    pids = load_watcher_pids()
    for agent_id, pid in pids.items():
        if is_pid_alive(pid):
            print(f"  [GUARD] Killing orphaned {agent_id} watcher (PID {pid})...")
            try:
                os.kill(int(pid), signal.SIGTERM)
            except: pass
    save_watcher_pids({})

cleanup_orphaned_watchers()

_AGENT_MAP = {
    'fullstack':  'crypto-fullstack',
    'data':       'crypto-data-engineer',
    'researcher': 'alpha-researcher',
    'developer':  'alpha-developer',
    'qa':         'crypto-qa-tester',
    'tuner':      'crypto-strategy-tuner',
}

_WATCHER_SCRIPT = os.path.join(ROOT_DIR, 'Crypto_Agent', 'agent_watcher.py')


@app.route('/api/agent_handshake', methods=['POST'])
def api_agent_handshake():
    """Bring an agent ONLINE: spawn its watcher process and enable boost if quant."""
    data     = request.json or {}
    agent_id = data.get('agent_id')

    if agent_id not in _AGENT_MAP:
        return jsonify({'error': 'Invalid agent ID'}), 400

    agent_name = _AGENT_MAP[agent_id]

    pids = load_watcher_pids()
    if agent_id in pids and is_pid_alive(pids[agent_id]):
        return jsonify({'message': f'{agent_name} is already ONLINE (PID {pids[agent_id]})'})

    try:
        proc = subprocess.Popen(
            [VENV_PYTHON, _WATCHER_SCRIPT, agent_id],
            cwd=ROOT_DIR,
            start_new_session=True,
        )
        pids[agent_id] = proc.pid
        save_watcher_pids(pids)
        return jsonify({'message': f'{agent_name} is now ONLINE (PID {proc.pid})'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent_offline', methods=['POST'])
def api_agent_offline():
    """Take an agent OFFLINE. For quant, keep process alive but disable boost."""
    data     = request.json or {}
    agent_id = data.get('agent_id')

    if agent_id not in _AGENT_MAP:
        return jsonify({'error': 'Invalid agent ID'}), 400

    agent_name = _AGENT_MAP[agent_id]
    agent_dir  = os.path.join(ROOT_DIR, '.gemini', 'skills', agent_name)
    pids = load_watcher_pids()
    
    # Standard offline logic: check persistence then pgrep for absolute safety
    pid_to_kill = pids.get(agent_id)
    if pid_to_kill and is_pid_alive(pid_to_kill):
        os.kill(int(pid_to_kill), signal.SIGTERM)
        pids.pop(agent_id, None)
        save_watcher_pids(pids)

    # Double-check pgrep for any orphans not in JSON
    try:
        orphans = subprocess.check_output(['pgrep', '-f', f'agent_watcher.py {agent_id}']).decode().split()
        for opid in orphans:
            try:
                os.kill(int(opid), signal.SIGTERM)
            except: pass
    except: pass

    hb_path = os.path.join(agent_dir, 'heartbeat.json')
    try:
        with open(hb_path, 'w') as f:
            json.dump({'ts': datetime.now().isoformat(),
                       'status': 'OFFLINE', 'action': 'Stopped by user'}, f, indent=2)
    except Exception:
        pass

    return jsonify({'message': f'{agent_name} is now OFFLINE'})


@app.route('/api/agent_mode', methods=['POST'])
def api_agent_mode():
    """Set agent mode: active (full autonomous), standby (inbox-only), or offline (kill)."""
    data     = request.json or {}
    agent_id = data.get('agent_id')
    mode     = data.get('mode')

    if agent_id not in _AGENT_MAP:
        return jsonify({'error': 'Invalid agent ID'}), 400
    if mode not in ('active', 'standby', 'offline'):
        return jsonify({'error': 'mode must be active | standby | offline'}), 400

    agent_name   = _AGENT_MAP[agent_id]
    agent_dir    = os.path.join(ROOT_DIR, '.gemini', 'skills', agent_name)
    standby_flag = os.path.join(agent_dir, 'standby_mode.flag')

    pids     = load_watcher_pids()
    is_alive = agent_id in pids and is_pid_alive(pids[agent_id])

    if mode == 'offline':
        if is_alive:
            os.kill(int(pids[agent_id]), signal.SIGTERM)
            pids.pop(agent_id, None)
            save_watcher_pids(pids)
        try:
            orphans = subprocess.check_output(
                ['pgrep', '-f', f'agent_watcher.py {agent_id}']).decode().split()
            for opid in orphans:
                try: os.kill(int(opid), signal.SIGTERM)
                except: pass
        except: pass
        try:
            with open(os.path.join(agent_dir, 'heartbeat.json'), 'w') as f:
                json.dump({'ts': datetime.now().isoformat(),
                           'status': 'OFFLINE', 'action': 'Stopped by user'}, f, indent=2)
        except: pass
        try: os.remove(standby_flag)
        except: pass
        return jsonify({'message': f'{agent_name} is now OFFLINE'})

    elif mode == 'standby':
        open(standby_flag, 'w').close()
        # Immediately stamp heartbeat as STANDBY so the dashboard doesn't
        # flip the toggle back before the watcher's 30s loop catches up.
        try:
            hb_path = os.path.join(agent_dir, 'heartbeat.json')
            with open(hb_path, 'r') as f:
                hb = json.load(f)
            hb['status'] = 'STANDBY'
            with open(hb_path, 'w') as f:
                json.dump(hb, f, indent=2)
        except Exception:
            pass
        if not is_alive:
            proc = subprocess.Popen(
                [VENV_PYTHON, _WATCHER_SCRIPT, agent_id],
                cwd=ROOT_DIR, start_new_session=True)
            pids[agent_id] = proc.pid
            save_watcher_pids(pids)
        return jsonify({'message': f'{agent_name} is now STANDBY (inbox-only, no scheduled tasks)'})

    else:  # active
        try: os.remove(standby_flag)
        except: pass
        # Immediately stamp heartbeat as ONLINE so the dashboard reflects the
        # change before the watcher's 30s loop fires.
        try:
            hb_path = os.path.join(agent_dir, 'heartbeat.json')
            with open(hb_path, 'r') as f:
                hb = json.load(f)
            hb['status'] = 'ONLINE'
            with open(hb_path, 'w') as f:
                json.dump(hb, f, indent=2)
        except Exception:
            pass
        if not is_alive:
            proc = subprocess.Popen(
                [VENV_PYTHON, _WATCHER_SCRIPT, agent_id],
                cwd=ROOT_DIR, start_new_session=True)
            pids[agent_id] = proc.pid
            save_watcher_pids(pids)
        return jsonify({'message': f'{agent_name} is now ACTIVE (full autonomous mode)'})


@app.route('/api/failure_report')
def api_failure_report():
    """Aggregate all failure events: system errors, scan BAD/ERROR, QA fails, dead letters."""
    failures = []

    # 1. System error log (.gemini/logs/error_log.jsonl) — only last 30 days to suppress stale entries
    error_log = os.path.join(ROOT_DIR, '.gemini', 'logs', 'error_log.jsonl')
    _cutoff_ts = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
    if os.path.exists(error_log):
        try:
            with open(error_log, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entry_ts = entry.get('ts', '')
                        if entry_ts and entry_ts < _cutoff_ts:
                            continue  # skip entries older than 30 days
                        msg = entry.get('error', '')
                        sid_m = re.search(r'Strategy\s+(\d+)', msg)
                        failures.append({
                            'ts':     entry_ts,
                            'type':   'SYSTEM_ERROR',
                            'name':   msg[:70],
                            'id':     sid_m.group(1) if sid_m else 'N/A',
                            'stage':  'RUNTIME',
                            'reason': msg,
                        })
                    except Exception:
                        pass
        except Exception:
            pass

    # 2. Strategy scan failures (grade BAD or ERROR)
    sr_path = os.path.join(ROOT_DIR, '.gemini', 'skills',
                           'crypto-strategy-tuner', 'data', 'scan_results.json')
    if os.path.exists(sr_path):
        try:
            sr = json.load(open(sr_path))
            scanned_at = sr.get('scanned_at', '')
            for v in sr.get('results', []):
                grade = v.get('grade', '')
                if grade in ('BAD', 'ERROR'):
                    failures.append({
                        'ts':     scanned_at,
                        'type':   'STRATEGY_FAILED',
                        'name':   v.get('class', f'Strategy {v.get("id","?")}'),
                        'id':     str(v.get('id', 'N/A')),
                        'stage':  'BACKTEST',
                        'reason': v.get('grade_reason', f'Grade: {grade}'),
                    })
        except Exception:
            pass

    # 3. QA failures
    qa_log = os.path.join(ROOT_DIR, '.gemini', 'skills',
                          'crypto-qa-tester', 'logs', 'qa_results.log')
    if os.path.exists(qa_log):
        try:
            with open(qa_log, 'r', errors='ignore') as f:
                for line in f:
                    if '[FAIL]' not in line:
                        continue
                    ts_m   = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                    sid_m  = re.search(r'sid=(\d+)', line)
                    rest   = line[line.find('[FAIL]') + 6:].strip().lstrip('✗✘ ')
                    parts  = rest.split(':', 1)
                    name   = parts[0].strip()
                    reason = parts[1].strip() if len(parts) > 1 else name
                    failures.append({
                        'ts':     ts_m.group(1).replace(' ', 'T') if ts_m else '',
                        'type':   'QA_FAIL',
                        'name':   name[:60],
                        'id':     sid_m.group(1) if sid_m else 'N/A',
                        'stage':  'QA',
                        'reason': reason[:120],
                    })
        except Exception:
            pass

    # 4. Dead-letter inbox messages
    for agent_dir in glob.glob(os.path.join(ROOT_DIR, '.gemini', 'skills', '*')):
        dead_dir = os.path.join(agent_dir, 'inbox', 'dead_letter')
        if not os.path.isdir(dead_dir):
            continue
        agent_name = os.path.basename(agent_dir)
        for fpath in sorted(glob.glob(os.path.join(dead_dir, '*.json'))):
            try:
                with open(fpath) as f:
                    msg = json.load(f)
                fname = os.path.basename(fpath)
                ts_m  = re.match(r'(\d{8})_(\d{6})', fname)
                ts    = ''
                if ts_m:
                    d, t = ts_m.group(1), ts_m.group(2)
                    ts = f'{d[:4]}-{d[4:6]}-{d[6:8]}T{t[:2]}:{t[2:4]}:{t[4:6]}'
                failures.append({
                    'ts':     ts or msg.get('ts', ''),
                    'type':   'DEAD_LETTER',
                    'name':   msg.get('topic', fname)[:60],
                    'id':     'N/A',
                    'stage':  f'INBOX → {agent_name}',
                    'reason': str(msg.get('message', msg.get('instruction', 'Undeliverable')))[:120],
                })
            except Exception:
                pass

    # 5. Professional Autopsy Reports (alpha_forge_v2/autopsy_report/)
    autopsy_dir = os.path.join(ROOT_DIR, 'phase_6_agent_monitor', 'alpha_forge_v2', 'autopsy_report')
    if os.path.isdir(autopsy_dir):
        for fpath in glob.glob(os.path.join(autopsy_dir, '**', '*.md'), recursive=True):
            fname = os.path.basename(fpath)
            if 'template' in fname.lower() or fname.lower() == 'readme.md':
                continue
            try:
                with open(fpath, 'r', errors='ignore') as fh:
                    content = fh.read()
                
                # Extract meta from frontmatter or filename
                name = os.path.splitext(fname)[0]
                ts = datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
                
                # Try to parse frontmatter for better metadata
                sid = 'N/A'
                if 'strategy_id:' in content:
                    m = re.search(r'strategy_id:\s*(.+)', content)
                    if m: sid = m.group(1).strip()
                
                rel = fpath.replace(ROOT_DIR + os.sep, '')
                failures.append({
                    'ts':     ts,
                    'type':   'AUTOPSY',
                    'name':   name.replace('_', ' '),
                    'id':     sid,
                    'stage':  'MORTALITY',
                    'reason': 'Click to view post-mortem report',
                    'file':   rel
                })
            except Exception:
                pass

    failures.sort(key=lambda x: x.get('ts', ''), reverse=True)
    return jsonify(failures[:100])


@app.route('/api/read_card')
def api_read_card():
    """Return the raw content of a factor-library card (.md file)."""
    rel = request.args.get('file', '')
    if not rel or '..' in rel:
        return jsonify({'error': 'Invalid file path'}), 400
    full = os.path.join(ROOT_DIR, rel)
    if not os.path.isfile(full):
        return jsonify({'error': f'File not found: {rel}'}), 404
    try:
        with open(full, 'r', errors='ignore') as fh:
            raw = fh.read()
        # Parse frontmatter (lines between first two --- separators)
        lines = raw.splitlines()
        frontmatter = {}
        status = 'QUEUED'
        body_start = 0
        if lines and lines[0].strip() == '---':
            end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == '---'), None)
            if end:
                for l in lines[1:end]:
                    if ':' in l:
                        k, _, v = l.partition(':')
                        frontmatter[k.strip()] = v.strip()
                body_start = end + 1
        status = frontmatter.get('status', frontmatter.get('Status', 'QUEUED')).upper()
        body = lines[body_start:]
        return jsonify({'status': status, 'frontmatter': frontmatter, 'body': body})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dispatch_to_researcher', methods=['POST'])
def api_dispatch_to_researcher():
    """Queue a factor card for the alpha-researcher to pick up."""
    data = request.json or {}
    rel_file = data.get('file', '')
    if not rel_file:
        return jsonify({'error': 'file is required'}), 400
    card_name = os.path.splitext(os.path.basename(rel_file))[0]
    inbox_dir = os.path.join(ROOT_DIR, '.gemini', 'skills', 'alpha-researcher', 'inbox')
    os.makedirs(inbox_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    payload = {
        'from': 'dashboard',
        'priority': 'HIGH',
        'topic': 'CARD_DISPATCH',
        'message': f'Dashboard dispatched factor card "{card_name}" for research. File: {rel_file}',
        'card_file': rel_file,
        'card_name': card_name,
        'ts': datetime.now().isoformat(),
    }
    try:
        fname = f'{ts}_from_dashboard_CARD_DISPATCH.json'
        with open(os.path.join(inbox_dir, fname), 'w') as f:
            json.dump(payload, f, indent=2)
        return jsonify({'message': f'Card "{card_name}" dispatched to alpha-researcher inbox.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent_telemetry')
def api_agent_telemetry():
    """
    Unified endpoint for the Phase 6 Command Center.
    Returns agent logs, collaboration ledger, heartbeats, and system stats.
    """
    def get_last_lines(path, n=15):
        if not os.path.exists(path): return []
        with open(path, 'r') as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-n:]]

    def get_heartbeat(agent_name):
        path = os.path.join(ROOT_DIR, '.gemini', 'skills', agent_name, 'heartbeat.json')
        if not os.path.exists(path):
            return {'status': 'OFFLINE', 'action': 'No heartbeat found', 'ts': None}
        try:
            with open(path, 'r') as f:
                hb = json.load(f)
            # Check if heartbeat is older than 10 minutes
            # Strip timezone info — all timestamps are now naive local (MYT)
            hb_time = datetime.fromisoformat(hb['ts'].split('+')[0].rstrip('Z'))
            if datetime.now() - hb_time > timedelta(minutes=10):
                hb['status'] = 'OFFLINE'
            return hb
        except:
            return {'status': 'OFFLINE', 'action': 'Error reading heartbeat', 'ts': None}

    agent_path = os.path.join(ROOT_DIR, '.gemini', 'skills')

    def get_all_lines(path, max_n=500):
        if not os.path.exists(path): return []
        with open(path, 'r') as f:
            lines = f.readlines()
        return [l.strip() for l in lines[-max_n:]]

    def count_errors_1h(agent_name):
        lines = get_all_lines(os.path.join(agent_path, agent_name, 'activity.log'), 300)
        cutoff = datetime.now() - timedelta(hours=1)
        count = 0
        for line in lines:
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if m:
                try:
                    ts = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                    if ts > cutoff and ('[ERROR]' in line or 'Error executing' in line):
                        count += 1
                except Exception:
                    pass
        return count

    def get_timeline_events(agent_name):
        lines = get_all_lines(os.path.join(agent_path, agent_name, 'activity.log'), 500)
        cutoff = datetime.now() - timedelta(hours=24)
        window_secs = 24 * 3600
        events = []
        for line in lines:
            m = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (.+)', line)
            if not m:
                continue
            try:
                ts = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
            if ts < cutoff:
                continue
            msg = m.group(2)
            if 'ONLINE' in msg and 'OFFLINE' not in msg:
                etype = 'online'
            elif 'OFFLINE' in msg:
                etype = 'offline'
            elif '✓' in msg or 'DONE' in msg or 'Completed' in msg or 'COMPLETE' in msg:
                etype = 'done'
            elif '[ERROR]' in msg or 'Error executing' in msg:
                etype = 'error'
            elif 'Quota hit' in msg or 'quota' in msg.lower():
                etype = 'quota'
            elif '▶' in msg or 'GEMINI START' in msg:
                etype = 'start'
            else:
                etype = 'info'
            pct = round((ts - cutoff).total_seconds() / window_secs * 100, 1)
            events.append({'ts': ts.strftime('%H:%M'), 'msg': msg[:80], 'type': etype, 'pct': pct})
        return events

    # 1. Agent Logs & Heartbeats
    agents = ['crypto-fullstack', 'crypto-data-engineer', 'alpha-researcher', 'alpha-developer', 'crypto-qa-tester', 'crypto-strategy-tuner']
    heartbeats = {a: get_heartbeat(a) for a in agents}

    logs = {
        'fullstack':  get_last_lines(os.path.join(agent_path, 'crypto-fullstack',      'activity.log')),
        'data':       get_last_lines(os.path.join(agent_path, 'crypto-data-engineer',  'activity.log')),
        'researcher': get_last_lines(os.path.join(agent_path, 'alpha-researcher',      'activity.log')),
        'developer':  get_last_lines(os.path.join(agent_path, 'alpha-developer',       'activity.log')),
        'qa':         get_last_lines(os.path.join(agent_path, 'crypto-qa-tester',      'activity.log')),
        'tuner':      get_last_lines(os.path.join(agent_path, 'crypto-strategy-tuner', 'activity.log')),
        'health':     get_last_lines(os.path.join(agent_path, 'crypto-data-engineer',  'logs', 'system_health.log'), 60),
        'qa_results': get_last_lines(os.path.join(agent_path, 'crypto-qa-tester',      'logs', 'qa_results.log'), 40),
    }

    # Changes log per agent (last 20 entries each)
    changes_logs = {
        'fullstack':  get_last_lines(os.path.join(agent_path, 'crypto-fullstack',      'changes.log'), 20),
        'data':       get_last_lines(os.path.join(agent_path, 'crypto-data-engineer',  'changes.log'), 20),
        'researcher': get_last_lines(os.path.join(agent_path, 'alpha-researcher',      'changes.log'), 20),
        'developer':  get_last_lines(os.path.join(agent_path, 'alpha-developer',       'changes.log'), 20),
        'qa':         get_last_lines(os.path.join(agent_path, 'crypto-qa-tester',      'changes.log'), 20),
        'tuner':      get_last_lines(os.path.join(agent_path, 'crypto-strategy-tuner', 'changes.log'), 20),
    }

    # Session log per agent (last 100 lines for reasoning & background output)
    session_logs = {
        'fullstack':  get_last_lines(os.path.join(agent_path, 'crypto-fullstack',      'session_memory'), 100),
        'data':       get_last_lines(os.path.join(agent_path, 'crypto-data-engineer',  'session_memory'), 100),
        'researcher': get_last_lines(os.path.join(agent_path, 'alpha-researcher',      'session_memory'), 100),
        'developer':  get_last_lines(os.path.join(agent_path, 'alpha-developer',       'session_memory'), 100),
        'qa':         get_last_lines(os.path.join(agent_path, 'crypto-qa-tester',      'session_memory'), 100),
        'tuner':      get_last_lines(os.path.join(agent_path, 'crypto-strategy-tuner', 'session_memory'), 100),
    }

    # Strategy tuner scan results
    scan_results_path = os.path.join(agent_path, 'crypto-strategy-tuner', 'data', 'scan_results.json')
    scan_results = {}
    if os.path.exists(scan_results_path):
        try:
            with open(scan_results_path) as f:
                scan_results = json.load(f)
        except Exception:
            pass
    force_rescan_flag = os.path.join(agent_path, 'crypto-strategy-tuner', 'data', 'force_rescan.flag')
    scan_results['_force_rescan_pending'] = os.path.exists(force_rescan_flag)

    # System-wide changelog (last 50 lines)
    system_changelog = get_last_lines(os.path.join(ROOT_DIR, '.gemini', 'shared', 'SYSTEM_CHANGELOG.md'), 50)

    # 2. Collaboration Ledger — task log lines for the collab feed (keep last 80)
    collab_path = os.path.join(ROOT_DIR, '.gemini', 'shared', 'AGENT_COLLABORATION.md')
    collab_data = get_last_lines(collab_path, 80)

    # 3. Active Flags from AGENT_COLLABORATION.md
    active_flags = []
    in_flags = False
    all_collab = []
    if os.path.exists(collab_path):
        with open(collab_path) as f:
            all_collab = f.read().splitlines()
    for line in all_collab:
            if '## Active Flags' in line:
                in_flags = True
                continue
            if in_flags:
                if line.startswith('## '):
                    break
                if not line.startswith('|'):
                    continue
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if not cells or all(c.startswith('-') for c in cells):
                    continue
                if cells[0].lower() == 'flag':
                    continue
                active_flags.append({'flag': cells[0] if len(cells) > 0 else '',
                                     'raised_by': cells[1] if len(cells) > 1 else '',
                                     'details': cells[2] if len(cells) > 2 else ''})

    # 5. Cross-agent inbox messages (include active/ folder)
    inbox_messages = []
    for agent in agents:
        inbox_dir = os.path.join(agent_path, agent, 'inbox')
        active_dir = os.path.join(inbox_dir, 'active')
        
        # Scan both root and active
        paths = glob.glob(os.path.join(inbox_dir, '*.json')) + \
                glob.glob(os.path.join(active_dir, '*.json'))
                
        for fpath in sorted(paths, reverse=True):
            try:
                with open(fpath) as f:
                    msg = json.load(f)
                msg['_to'] = agent
                msg['_file'] = os.path.basename(fpath)
                # Flag if it's currently being worked on
                if 'active/' in fpath:
                    msg['_status'] = 'PROCESSING'
                else:
                    msg['_status'] = 'PENDING'
                inbox_messages.append(msg)
            except Exception:
                pass

    # 6. Archive resolved inbox messages + fetch history
    _archive_resolved_inbox(inbox_messages)
    resolved_inbox = _get_resolved_inbox(15)

    # 7. Health summary (counts from health log)
    health_lines = logs['health']
    health_summary = {
        'errors': sum(1 for l in health_lines if '[ERROR]' in l),
        'warns':  sum(1 for l in health_lines if '[WARN]' in l),
        'oks':    sum(1 for l in health_lines if '[OK]' in l),
    }

    # 8. Error counts per agent (last 1h)
    error_counts = {
        'fullstack':  count_errors_1h('crypto-fullstack'),
        'data':       count_errors_1h('crypto-data-engineer'),
        'researcher': count_errors_1h('alpha-researcher'),
        'developer':  count_errors_1h('alpha-developer'),
        'qa':         count_errors_1h('crypto-qa-tester'),
        'tuner':      count_errors_1h('crypto-strategy-tuner'),
    }

    # 9. Activity timeline (last 24h per agent)
    timeline = {
        'fullstack':  get_timeline_events('crypto-fullstack'),
        'data':       get_timeline_events('crypto-data-engineer'),
        'researcher': get_timeline_events('alpha-researcher'),
        'developer':  get_timeline_events('alpha-developer'),
        'qa':         get_timeline_events('crypto-qa-tester'),
        'tuner':      get_timeline_events('crypto-strategy-tuner'),
    }

    # 10. Model usage — parse all activity logs for GEMINI START / DONE / Quota hits
    def parse_model_usage():
        agent_log_map = {
            'fullstack':  os.path.join(agent_path, 'crypto-fullstack',      'activity.log'),
            'data':       os.path.join(agent_path, 'crypto-data-engineer',  'activity.log'),
            'researcher': os.path.join(agent_path, 'alpha-researcher',      'activity.log'),
            'developer':  os.path.join(agent_path, 'alpha-developer',       'activity.log'),
            'qa':         os.path.join(agent_path, 'crypto-qa-tester',      'activity.log'),
            'tuner':      os.path.join(agent_path, 'crypto-strategy-tuner', 'activity.log'),
        }
        re_ts    = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]')
        re_start = re.compile(r'▶ GEMINI START — .+\[([^\]]+)\]')
        re_done  = re.compile(r'✓ GEMINI DONE — .+\[([^\]]+)\] \((\d+)s\)')
        re_quota = re.compile(r'⚠ Quota hit on ([^\s(]+)')

        usage = {}  # model → {calls, completed, total_secs, quota_hits, last_used_ts, last_used_agent}

        for agent_id, log_path in agent_log_map.items():
            lines = get_all_lines(log_path, 1000)
            for line in lines:
                ts_m = re_ts.match(line)
                ts_str = ts_m.group(1) if ts_m else None

                m = re_start.search(line)
                if m:
                    model = m.group(1)
                    if model not in usage:
                        usage[model] = {'calls': 0, 'completed': 0, 'total_secs': 0,
                                        'quota_hits': 0, 'last_used_ts': None, 'last_used_agent': ''}
                    usage[model]['calls'] += 1
                    if ts_str and (usage[model]['last_used_ts'] is None or ts_str > usage[model]['last_used_ts']):
                        usage[model]['last_used_ts'] = ts_str
                        usage[model]['last_used_agent'] = agent_id
                    continue

                m = re_done.search(line)
                if m:
                    model, secs = m.group(1), int(m.group(2))
                    if model not in usage:
                        usage[model] = {'calls': 0, 'completed': 0, 'total_secs': 0,
                                        'quota_hits': 0, 'last_used_ts': None, 'last_used_agent': ''}
                    usage[model]['completed']  += 1
                    usage[model]['total_secs'] += secs
                    continue

                m = re_quota.search(line)
                if m:
                    model = m.group(1)
                    if model not in usage:
                        usage[model] = {'calls': 0, 'completed': 0, 'total_secs': 0,
                                        'quota_hits': 0, 'last_used_ts': None, 'last_used_agent': ''}
                    usage[model]['quota_hits'] += 1

        # Compute avg_secs and format last_used
        result = []
        for model, d in usage.items():
            avg = round(d['total_secs'] / d['completed']) if d['completed'] > 0 else 0
            last = ''
            if d['last_used_ts']:
                try:
                    last = datetime.strptime(d['last_used_ts'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M %d/%m')
                except Exception:
                    last = d['last_used_ts'][:16]
            result.append({
                'model':       model,
                'calls':       d['calls'],
                'completed':   d['completed'],
                'avg_secs':    avg,
                'quota_hits':  d['quota_hits'],
                'last_used':   last,
                'agent':       d['last_used_agent'],
            })
        result.sort(key=lambda x: x['calls'], reverse=True)
        return result

    model_usage = parse_model_usage()

    # 10. System Stats
    import shutil
    total, used, free = shutil.disk_usage("/")

    # Per-agent watcher PID status
    pids_map = load_watcher_pids()
    watcher_pids = {}
    alive_watcher_count = 0
    for aid in ['fullstack', 'data', 'researcher', 'developer', 'qa', 'tuner']:
        pid = pids_map.get(aid)
        alive = is_pid_alive(pid) if pid else False
        if alive:
            alive_watcher_count += 1
        watcher_pids[aid] = {'pid': pid, 'alive': alive}

    # 11. Pipeline stats — Alpha Forge funnel
    def build_pipeline_stats():
        import glob as _glob
        forge_dir = os.path.join(ROOT_DIR, 'phase_6_agent_monitor', 'alpha_forge_v2')

        def _read_md_items(directory, default_status='DRAFT'):
            """Read all .md files and parse their full YAML frontmatter."""
            os.makedirs(directory, exist_ok=True)
            items = []
            for fpath in sorted(_glob.glob(os.path.join(directory, '**', '*.md'), recursive=True)):
                fname = os.path.basename(fpath)
                if 'template' in fname.lower() or fname.lower() == 'readme.md':
                    continue
                
                meta = {'status': default_status, 'name': os.path.splitext(fname)[0]}
                try:
                    with open(fpath, 'r', errors='ignore') as fh:
                        content = fh.read()
                    
                    # Basic YAML frontmatter parser
                    if content.startswith('---'):
                        _, fm_text, _ = content.split('---', 2)
                        for line in fm_text.strip().split('\n'):
                            if ':' in line:
                                k, v = line.split(':', 1)
                                meta[k.strip().lower()] = v.strip()
                except Exception:
                    pass
                
                # Ensure status is uppercase
                meta['status'] = meta.get('status', default_status).upper()
                
                rel = fpath.replace(ROOT_DIR + os.sep, '')
                parent = os.path.basename(os.path.dirname(fpath))
                category = parent if parent != os.path.basename(directory) else None
                
                meta.update({'file': rel, 'category': category})
                items.append(meta)
            return items

        # Stage 0: raw factor cards from factor_library/, categorised by sub-folder
        factor_dir = os.path.join(ROOT_DIR, 'factor_library')
        cards = []
        for fpath in _glob.glob(os.path.join(factor_dir, '**', '*.md'), recursive=True):
            fname = os.path.basename(fpath)
            if 'template' in fname.lower() or fname.lower() == 'readme.md':
                continue
            parent = os.path.basename(os.path.dirname(fpath))
            category = 'Uncategorized' if parent in ('factor_library', '') or parent.startswith('.') else parent
            # Skip utility folders (_Concepts, _Index, etc.) and underscore files
            if category.startswith('_') or fname.startswith('_'):
                continue
            status = 'QUEUED'
            name = os.path.splitext(fname)[0]
            try:
                with open(fpath, 'r', errors='ignore') as fh:
                    for line in fh:
                        if line.strip().lower().startswith('status:'):
                            status = line.split(':', 1)[1].strip().upper()
                            break
            except Exception:
                pass
            rel = fpath.replace(ROOT_DIR + os.sep, '')
            cards.append({'name': name, 'status': status, 'file': rel, 'category': category})

        stage0_total    = len(cards)
        stage0_built    = sum(1 for c in cards if c['status'] in ('IMPLEMENTED',))
        stage0_rejected = sum(1 for c in cards if c['status'] in ('REJECTED',))
        stage0_pending  = sum(1 for c in cards if c['status'] in ('QUEUED', 'PENDING'))

        # Stage 1: hypothesis reports written by alpha-researcher
        hypho_items  = _read_md_items(os.path.join(forge_dir, 'hypho_report'), 'DRAFT')
        stage1_count = len(hypho_items)

        # Stage 2: development + initial backtest reports written by alpha-developer
        dev_items    = _read_md_items(os.path.join(forge_dir, 'dev_report'), 'IN_PROGRESS')
        stage2_count = len(dev_items)

        # Stage 3: backtest + stability reports generated by strategy-tuner
        backtest_items = _read_md_items(os.path.join(forge_dir, 'backtest_report'), 'SCANNED')
        stage3_count   = len(backtest_items)

        # Stage 4: elite strategies with Market Fit Memos
        elite_items  = _read_md_items(os.path.join(forge_dir, 'elite_report'), 'PAPER_READY')
        stage4_count = len(elite_items)
        stage4_items = elite_items

        graveyard_count = 0
        sr_path = os.path.join(agent_path, 'crypto-strategy-tuner', 'data', 'scan_results.json')
        if os.path.exists(sr_path):
            try:
                sr = json.load(open(sr_path))
                for v in sr.get('results', []):
                    if v.get('grade', '') in ('BAD', 'ERROR'):
                        graveyard_count += 1
            except Exception:
                pass

        # Also count QA failures and dead letters in the graveyard
        qa_log = os.path.join(agent_path, 'crypto-qa-tester', 'logs', 'qa_results.log')
        if os.path.exists(qa_log):
            try:
                with open(qa_log, 'r', errors='ignore') as f:
                    graveyard_count += sum(1 for line in f if '[FAIL]' in line)
            except Exception:
                pass

        for _adir in _glob.glob(os.path.join(agent_path, '*', 'inbox', 'dead_letter', '*.json')):
            graveyard_count += 1

        stage4_count = len(stage4_items)

        return {
            'stage0':          stage0_total,
            'stage0_built':    stage0_built,
            'stage0_rejected': stage0_rejected,
            'stage0_pending':  stage0_pending,
            'stage0_items':    cards,
            'stage1':         stage1_count,
            'stage1_items':   hypho_items,
            'stage2':         stage2_count,
            'stage2_items':   dev_items,
            'stage3':         stage3_count,
            'stage3_items':   backtest_items,
            'stage4':         stage4_count,
            'stage4_items':   stage4_items,
            'stage5':         0,
            'graveyard':      graveyard_count,
        }

    pipeline_stats = build_pipeline_stats()

    return jsonify({
        'logs': logs,
        'heartbeats': heartbeats,
        'collab': collab_data,
        'active_flags': active_flags,
        'inbox_messages': inbox_messages,
        'resolved_inbox': resolved_inbox,
        'inbox_counts': {
            a: len(glob.glob(os.path.join(agent_path, a, 'inbox', '*.json')))
            for a in agents
        },
        'qa_results': logs.get('qa_results', []),
        'changes_logs': changes_logs,
        'session_logs': session_logs,
        'system_changelog': system_changelog,
        'health_summary': health_summary,
        'error_counts': error_counts,
        'timeline': timeline,
        'model_usage':   model_usage,
        'scan_results':  scan_results,
        'watcher_pids':   watcher_pids,
        'pipeline_stats': pipeline_stats,
        'system': {
            'disk_free_gb': round(free / (1024**3), 2),
            'active_python_processes': alive_watcher_count,
            'last_update': datetime.now().strftime("%H:%M:%S")
        },
        'status': load_state().get('phases', {})
    })

@app.route('/datasets')
def list_datasets():
    dataset_dir = os.path.join(ROOT_DIR, 'dataset')
    results = {}
    if os.path.exists(dataset_dir):
        for coin in os.listdir(dataset_dir):
            coin_path = os.path.join(dataset_dir, coin)
            if os.path.isdir(coin_path):
                results[coin] = []
                for tf in os.listdir(coin_path):
                    tf_path = os.path.join(coin_path, tf)
                    if os.path.isdir(tf_path):
                        parquet = os.path.join(tf_path, 'spot_ohlcv.parquet')
                        if os.path.exists(parquet):
                            stats = os.stat(parquet)
                            results[coin].append({
                                "timeframe": tf,
                                "size": f"{stats.st_size / (1024*1024):.2f} MB",
                                "last_modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d")
                            })
    return jsonify(results)

@app.route('/processed')
def list_processed():
    data_dir = os.path.join(ROOT_DIR, 'data')
    results = {"trainval": [], "trade": []}
    
    if os.path.exists(data_dir):
        # Processed Train/Val (Directly under data/, excluding trade_data)
        for d in os.listdir(data_dir):
            if d == 'trade_data' or not os.path.isdir(os.path.join(data_dir, d)):
                continue
            meta_path = os.path.join(data_dir, d, 'metadata.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    results["trainval"].append({
                        "folder": d,
                        "metadata": json.load(f)
                    })
        
        # Processed Trade
        trade_dir = os.path.join(data_dir, 'trade_data')
        if os.path.exists(trade_dir):
            for d in os.listdir(trade_dir):
                if not os.path.isdir(os.path.join(trade_dir, d)):
                    continue
                meta_path = os.path.join(trade_dir, d, 'metadata.json')
                if os.path.exists(meta_path):
                    with open(meta_path, 'r') as f:
                        results["trade"].append({
                            "folder": d,
                            "metadata": json.load(f)
                        })
    return jsonify(results)

@app.route('/data_preview')
def data_preview():
    preview_type = request.args.get('type')
    
    try:
        if preview_type == 'raw':
            coin = request.args.get('coin')
            tf = request.args.get('tf')
            path = os.path.join(ROOT_DIR, 'dataset', coin, tf, 'spot_ohlcv.parquet')
            if not os.path.exists(path):
                return jsonify({"error": "Dataset not found"}), 404
            
            df = pd.read_parquet(path)
            # Sample data if too large for performance
            if len(df) > 5000:
                df = df.iloc[::max(1, len(df)//2000)]
            
            # Standardize time column for preview (Binance uses open_time, Yahoo uses timestamp)
            time_col = 'open_time' if 'open_time' in df.columns else 'timestamp'
            
            return jsonify({
                "times": df[time_col].dt.strftime('%Y-%m-%d %H:%M').tolist(),
                "prices": df['close'].tolist(),
                "title": f"Raw {coin} ({tf})"
            })
            
        elif preview_type == 'processed':
            folder = request.args.get('folder')
            is_trade = request.args.get('trade') == 'true'
            
            base_dir = os.path.join(ROOT_DIR, 'data', 'trade_data' if is_trade else '')
            folder_path = os.path.join(base_dir, folder)
            
            price_path = os.path.join(folder_path, 'price_array')
            time_path = os.path.join(folder_path, 'time_array')
            meta_path = os.path.join(folder_path, 'metadata.json')
            
            if not all(os.path.exists(p) for p in [price_path, time_path, meta_path]):
                return jsonify({"error": "Processed files missing"}), 404
            
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            prices = np.load(price_path, allow_pickle=True)
            times = np.load(time_path, allow_pickle=True)
            
            # prices shape is (steps, tickers)
            # Use the first ticker for preview
            preview_prices = prices[:, 0].tolist()
            
            # Convert numpy/pandas times to strings
            formatted_times = []
            for t in times:
                if hasattr(t, 'strftime'):
                    formatted_times.append(t.strftime('%Y-%m-%d %H:%M'))
                else:
                    formatted_times.append(str(t))
                
            return jsonify({
                "times": formatted_times,
                "prices": preview_prices,
                "title": f"Processed: {folder} ({meta['tickers'][0]})"
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid request"}), 400

@app.route('/trigger_validate', methods=['POST'])
def trigger_validate():
    phase = 'phase_2'
    print(f"Triggering {phase} Validation...")
    try:
        results_dir = os.path.join(ROOT_DIR, 'train_results')
        if not os.path.exists(results_dir):
            return jsonify({"error": "No train_results directory found"}), 404
            
        # Find latest result
        res_folders = [d for d in os.listdir(results_dir) 
                       if os.path.isdir(os.path.join(results_dir, d)) and d.startswith('res_')]
        
        if not res_folders:
            return jsonify({"error": "No optimization results found to validate"}), 404
            
        res_folders.sort(key=lambda x: os.path.getmtime(os.path.join(results_dir, x)), reverse=True)
        latest_res = res_folders[0]
        print(f"Latest result found: {latest_res}")
        
        script_path = os.path.join(ROOT_DIR, 'phase_2', 'validate.py')
        log_path = os.path.join(CONTROLLER_DIR, f'{phase}.log')

        # Start as background process
        process = subprocess.Popen(
            [VENV_PYTHON, script_path, latest_res],
            stdout=open(log_path, 'w'),
            stderr=subprocess.STDOUT,
            cwd=ROOT_DIR,
            start_new_session=True 
        )
        active_processes[phase] = process
        update_phase_status(phase, 'running', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return jsonify({
            "message": "Validation started in background",
            "folder": latest_res
        })
            
    except Exception as e:
        print(f"Exception in trigger_validate: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def get_status():
    return jsonify(load_state())

@app.route('/list_results')
def list_results():
    results_dir = os.path.join(ROOT_DIR, 'train_results')
    folders = []
    if os.path.exists(results_dir):
        for d in os.listdir(results_dir):
            if os.path.isdir(os.path.join(results_dir, d)) and os.path.exists(os.path.join(results_dir, d, 'study.pkl')):
                folders.append(d)
    folders.sort(reverse=True)
    return jsonify(folders)

@app.route('/run/<phase>', methods=['POST'])
def run_phase(phase):
    state = load_state()
    if phase not in state['phases']:
        return jsonify({"error": "Invalid phase"}), 400
    
    if phase in active_processes and active_processes[phase].poll() is None:
        return jsonify({"error": "Phase already running"}), 400

    data = request.json or {}
    folder = data.get('folder')

    script_path = os.path.join(ROOT_DIR, state['phases'][phase]['script'])
    log_path = os.path.join(CONTROLLER_DIR, f'{phase}.log')
    
    cmd = [VENV_PYTHON, script_path]
    if folder:
        cmd.append(folder)

    # Start the process in the background
    try:
        process = subprocess.Popen(
            cmd,
            stdout=open(log_path, 'w'),
            stderr=subprocess.STDOUT,
            cwd=ROOT_DIR,
            start_new_session=True 
        )
        active_processes[phase] = process
        update_phase_status(phase, 'running', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return jsonify({"message": f"Started {phase}", "cmd": " ".join(cmd)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stop/<phase>', methods=['POST'])
def stop_phase(phase):
    if phase in active_processes:
        process = active_processes[phase]
        if process.poll() is None:
            try:
                # Use killpg to kill the process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                update_phase_status(phase, 'failed')
                return jsonify({"message": f"Stopped {phase}"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    # If not running or not in active_processes, update state and return success
    update_phase_status(phase, 'failed')
    return jsonify({"message": f"{phase} is not active"}), 200

def monitor_processes():
    state = load_state()
    changed = False
    for phase, process in list(active_processes.items()):
        poll = process.poll()
        if poll is not None:
            status = 'completed' if poll == 0 else 'failed'
            update_phase_status(phase, status)
            del active_processes[phase]
            changed = True
    return changed

@app.route('/check_updates')
def check_updates():
    try:
        monitor_processes()
    except Exception as e:
        print(f"  [ERROR] monitor_processes failed: {e}")
        
    try:
        refresh_metadata()
    except Exception as e:
        print(f"  [ERROR] refresh_metadata failed: {e}")
        
    return jsonify(load_state())

def _kill_all_watchers():
    """Kill all agent watcher children. Called by atexit AND SIGTERM."""
    print("\n[SHUTDOWN] Terminating all agent watchers...")
    pids = load_watcher_pids()
    for agent_id, pid in pids.items():
        if is_pid_alive(pid):
            print(f"  Killing {agent_id} watcher (PID {pid})")
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
    try:
        orphans = subprocess.check_output(
            ['pgrep', '-f', 'agent_watcher.py']).decode().split()
        for opid in orphans:
            try:
                os.kill(int(opid), signal.SIGTERM)
            except Exception:
                pass
    except Exception:
        pass
    save_watcher_pids({})
    print("[SHUTDOWN] Done. Goodbye.")

# atexit fires on Ctrl+C, kill, or normal exit — catches what signal handlers miss
import atexit
atexit.register(_kill_all_watchers)

# SIGTERM (e.g. from 'kill <pid>') still needs explicit handling
def _sigterm_handler(signum, frame):
    sys.exit(0)  # triggers atexit

signal.signal(signal.SIGTERM, _sigterm_handler)

@app.route('/api/multicoin_forge_files', methods=['GET', 'OPTIONS'])
def api_multicoin_forge_files():
    if request.method == 'OPTIONS':
        return '', 204
    results_dir = os.path.join(ROOT_DIR, 'strategy_forge', 'results')
    try:
        if not os.path.exists(results_dir):
            return jsonify({'files': []})
        files = []
        for fname in sorted(os.listdir(results_dir), reverse=True):
            if not fname.startswith('multi_forge_') or not fname.endswith('.json'):
                continue
            fpath = os.path.join(results_dir, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                files.append({
                    'filename': fname,
                    'run_at':   (data.get('run_at') or '')[:19].replace('T', ' '),
                    'coins':    data.get('coins', []),
                    'tfs':      data.get('tfs', []),
                    'n':        data.get('n', 0),
                    'hits':     len(data.get('results', [])),
                })
            except Exception:
                pass
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/multicoin_forge_load', methods=['GET', 'OPTIONS'])
def api_multicoin_forge_load():
    if request.method == 'OPTIONS':
        return '', 204
    filename = request.args.get('filename', '').strip()
    if not filename or not filename.startswith('multi_forge_') or not filename.endswith('.json'):
        return jsonify({'error': 'Invalid filename'}), 400
    fpath = os.path.join(ROOT_DIR, 'strategy_forge', 'results', os.path.basename(filename))
    if not os.path.exists(fpath):
        return jsonify({'error': 'File not found'}), 404
    try:
        with open(fpath) as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/multicoin_backtest', methods=['POST', 'OPTIONS'])
def api_multicoin_backtest():
    if request.method == 'OPTIONS':
        return '', 204

    data      = request.json or {}
    dnas      = data.get('dnas', [])       # [{rank, entry, filters, exit, params, tf}, ...]
    coins     = data.get('coins', [])
    date_from = str(data.get('date_from', '2021-01-01'))
    date_to   = str(data.get('date_to',   '2026-05-31'))

    if not dnas:
        return jsonify({'error': 'No DNA strategies provided'}), 400
    if not coins:
        return jsonify({'error': 'No coins selected'}), 400

    try:
        import importlib
        sys.path.insert(0, ROOT_DIR)

        with _reload_lock:
            for _mod_name in (
                'strategy_forge.indicators',
                'strategy_forge.signals.entry_signals',
                'strategy_forge.signals.filter_signals',
                'strategy_forge.signals.exit_signals',
                'strategy_forge.composer.dna',
            ):
                if _mod_name in sys.modules:
                    try:
                        importlib.reload(sys.modules[_mod_name])
                    except Exception:
                        pass

        from strategy_forge.composer.dna    import StrategyDNA
        from strategy_backtest.engine       import BacktestEngine
        from strategy_backtest.risk         import RiskManager
        from strategy_backtest.metrics      import compute_metrics, _extract_numeric
        from strategy_backtest.run_backtest import load_data

        # Default risk settings (standard forge risk)
        _RM_DEFAULTS = dict(risk_per_trade=0.02, leverage=3, trading_fee=0.0004, maintenance_margin_rate=0.005)
        INIT_BAL = 10_000.0

        results = []
        errors  = []

        for dna_spec in dnas:
            rank        = dna_spec.get('rank', 0)
            entry       = str(dna_spec.get('entry', ''))
            filters     = dna_spec.get('filters', [])
            exit_method = str(dna_spec.get('exit', ''))
            params      = dna_spec.get('params', {})
            tf          = str(dna_spec.get('tf', '1h'))
            coin_symbol = str(dna_spec.get('coin', '')).upper()  # ignored — we iterate below

            for coin in coins:
                try:
                    coin_u = coin.upper()
                    # Dataset uses bare symbol (BTC, ETH) — strip USDT suffix if present
                    data_symbol = coin_u[:-4] if coin_u.endswith('USDT') else coin_u
                    df = load_data(data_symbol, tf, date_from, date_to)
                    if df is None or df.empty or len(df) < 50:
                        print(f"  [MC] {coin} {tf}: no data — skip")
                        continue

                    strat = StrategyDNA(df, entry=entry, filters=filters, exit_method=exit_method, params=params)
                    rm    = RiskManager(**_RM_DEFAULTS)
                    engine = BacktestEngine(df, strat, rm, initial_balance=INIT_BAL)
                    equity = engine.run()

                    if not equity or len(equity) < 2:
                        continue

                    metrics_raw = compute_metrics(equity, INIT_BAL, timestamps=engine.df.index, trades=engine.trades)
                    metrics_num = _extract_numeric(metrics_raw)

                    init_bal   = INIT_BAL
                    cumret     = [round(v / init_bal - 1, 6) for v in equity]
                    n_pts      = len(cumret)
                    ts_raw     = [str(t) for t in engine.df.index[:n_pts]]
                    prices_raw = [round(float(v), 2) for v in engine.df['Close'].values[:n_pts]]

                    max_pts = 3000
                    if n_pts > max_pts:
                        step  = max(1, n_pts // max_pts)
                        ds_idx = list(range(0, n_pts, step))
                        ts_ds     = [ts_raw[i]     for i in ds_idx]
                        cr_ds     = [cumret[i]     for i in ds_idx]
                        prices_ds = [prices_raw[i] for i in ds_idx]
                    else:
                        ts_ds, cr_ds, prices_ds = ts_raw, cumret, prices_raw

                    periodic = {'monthly': {'labels': [], 'values': []},
                                'yearly':  {'labels': [], 'values': []}}
                    if 'MONTHLY_RETURNS' in metrics_raw:
                        mdata = metrics_raw['MONTHLY_RETURNS']
                        periodic['monthly'] = {
                            'labels': list(mdata.keys()),
                            'values': [float(v['return'].replace('%', '').replace('+', '')) for v in mdata.values()]
                        }
                    if 'YEARLY_RETURNS' in metrics_raw:
                        ydata = metrics_raw['YEARLY_RETURNS']
                        periodic['yearly'] = {
                            'labels': list(ydata.keys()),
                            'values': [float(v['return'].replace('%', '').replace('+', '')) for v in ydata.values()]
                        }

                    round_trips = []
                    entry_stack = []
                    for t in (engine.trades or []):
                        if t['type'] in ('BUY', 'SELL', 'BUY_ADD', 'SELL_ADD'):
                            entry_stack.append(t)
                        elif t['type'] in ('EXIT_LONG', 'EXIT_SHORT') and entry_stack:
                            is_long   = t['type'] == 'EXIT_LONG'
                            total_qty = sum(float(e.get('qty', 0)) for e in entry_stack)
                            avg_ep    = (sum(float(e.get('qty', 0)) * float(e.get('price', 0))
                                            for e in entry_stack) / total_qty) if total_qty > 0 else float(entry_stack[0].get('price', 0))
                            total_entry_fee      = sum(float(e.get('fee', 0))          for e in entry_stack)
                            total_entry_slippage = sum(float(e.get('slippage_usd', 0)) for e in entry_stack)
                            total_margin         = sum(float(e.get('margin', 0))       for e in entry_stack)
                            total_notional       = sum(float(e.get('notional', 0))     for e in entry_stack)
                            first_entry          = entry_stack[0]
                            exit_fee      = float(t.get('fee', 0))
                            exit_slippage = float(t.get('slippage_usd', 0))
                            gross_pnl     = float(t.get('gross_pnl', 0))
                            total_fees    = total_entry_fee + exit_fee
                            trade_net     = gross_pnl - total_fees
                            xp            = float(t.get('price', 0))
                            ep            = avg_ep
                            roe_pct       = round(trade_net / total_margin * 100, 2) if total_margin > 0 else 0.0
                            mkt_pct       = round((xp / ep - 1) * 100 if ep > 0 else 0, 2)
                            if not is_long:
                                mkt_pct = round((ep / xp - 1) * 100 if xp > 0 else 0, 2)
                            try:
                                dur = (t['time'] - first_entry['time']).days
                            except Exception:
                                dur = 0
                            round_trips.append({
                                'entry_time':    str(first_entry['time']),
                                'exit_time':     str(t['time']),
                                'side':          'LONG' if is_long else 'SHORT',
                                'qty':           round(total_qty, 6),
                                'entry_price':   round(ep, 4),
                                'exit_price':    round(xp, 4),
                                'gross_pnl':     round(gross_pnl, 2),
                                'total_fees':    round(total_fees, 2),
                                'slippage_usd':  round(total_entry_slippage + exit_slippage, 4),
                                'slippage_pct':  float(t.get('slippage_pct', 0)),
                                'net_profit':    round(trade_net, 2),
                                'mkt_pct':       mkt_pct,
                                'duration_days': dur,
                                'margin':        round(total_margin, 2),
                                'notional':      round(total_notional, 2),
                                'leverage':      int(first_entry.get('leverage', 0)),
                                'reason':        str(t.get('reason', '—')),
                                'roe_pct':       roe_pct,
                                'balance_after': round(float(t.get('balance_after', 0)), 2),
                            })
                            entry_stack = []

                    fmt_metrics = {}
                    for k, v in metrics_raw.items():
                        if k.startswith('MONTHLY') or k.startswith('YEARLY'):
                            continue
                        fmt_metrics[k] = str(v) if not isinstance(v, dict) else v

                    label = f"{entry}+[{','.join(filters)}]→{exit_method}" if filters else f"{entry}→{exit_method}"
                    results.append({
                        'rank':             rank,
                        'class':            label,
                        'desc':             f"#{rank} {entry} / {exit_method}",
                        'coin':             data_symbol,
                        'timeframe':        tf,
                        'initial_balance':  init_bal,
                        'leverage':         _RM_DEFAULTS['leverage'],
                        'equity_times':     ts_ds,
                        'equity_cumret':    cr_ds,
                        'equity_prices':    prices_ds,
                        'metrics':          metrics_num,
                        'fmt_metrics':      fmt_metrics,
                        'periodic':         periodic,
                        'round_trips':      round_trips,
                    })
                    print(f"  ✓ MC #{rank} {data_symbol} {tf}  Sharpe={metrics_num['Sharpe Ratio']:>6.2f}  "
                          f"Return={metrics_num['Total Return']:>7.1f}%  Trades={metrics_num['Total Trades']}")

                except Exception as e:
                    import traceback as _tb
                    errmsg = f"#{rank} {coin} {tf}: {type(e).__name__}: {e}"
                    print(f"  [WARN] MC {errmsg}")
                    _tb.print_exc()
                    errors.append(errmsg)

        return jsonify({'results': results, 'errors': errors, 'n_attempted': len(dnas) * len(coins)})

    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        trigger_gemini_debugger(str(e))
        return jsonify({'error': str(e)}), 500


def _check_strategy_library_integrity():
    """Warn on startup if STRATEGY_LIBRARY has ID gaps or missing strategy classes."""
    try:
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)
        import strategy_backtest.settings as _s
        import strategy_backtest.strategies as _sr
        def _parse_id(x):
            try:
                return int(x)
            except ValueError:
                try:
                    return int(str(x).split('_')[0])
                except ValueError:
                    return 0
        
        valid_keys = [k for k in _s.STRATEGY_LIBRARY.keys() if _parse_id(k) > 0]
        ids = sorted(valid_keys, key=_parse_id)
        nums = [_parse_id(x) for x in ids] if ids else []
        gaps = [i for i in range(min(nums), max(nums) + 1) if i not in nums] if nums else []
        missing_cls = [
            (sid, cfg['class'])
            for sid, cfg in _s.STRATEGY_LIBRARY.items()
            if not hasattr(_sr, cfg['class'])
        ]
        if gaps:
            print(f"⚠️  STRATEGY_LIBRARY integrity: missing IDs {gaps} — check settings.py")
        if missing_cls:
            print(f"⚠️  STRATEGY_LIBRARY integrity: class not found for {missing_cls}")
        if not gaps and not missing_cls:
            print(f"✓  STRATEGY_LIBRARY integrity OK ({len(_s.STRATEGY_LIBRARY.keys())} strategies, no gaps)")
    except Exception as e:
        print(f"⚠️  STRATEGY_LIBRARY integrity check failed: {e}")


if __name__ == "__main__":
    _check_strategy_library_integrity()
    print(f"Starting Crypto-RL Control Server on http://127.0.0.1:5001")
    app.run(port=5001, debug=False, use_reloader=False)
