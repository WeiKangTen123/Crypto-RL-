import os
import sys
import json
import argparse
import pandas as pd
from datetime import datetime

_script_dir = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(_script_dir)
sys.path.insert(0, ROOT_DIR)

from phase_7.scripts.regime_classifier import classify_regime, extract_market_features
from phase_7.scripts.window_tuner import optimize_window
from strategy_backtest.settings import STRATEGY_LIBRARY
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager
from strategy_backtest.metrics import compute_metrics, _extract_numeric
from strategy_backtest.run_backtest import load_data
import strategy_backtest.strategies as strat_reg

WISDOM_PATH = "phase_7/data/wisdom_matrix.csv"
RAW_DIR     = "phase_7/data/raw_results"


def raw_result_path(sid, window):
    return os.path.join(RAW_DIR, f"sid_{sid}_{window['type']}_{window['start']}.json")


def load_existing_summary(sid, window):
    """Return cached summary if already mined, else None."""
    path = raw_result_path(sid, window)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if all(k in data for k in ("roi", "sharpe", "regime", "category")):
            return {k: data[k] for k in (
                "strategy_id", "category", "window_type", "start_date", "end_date",
                "regime", "regime_score", "roi", "sharpe", "mdd", "trades",
                "market_features", "params"
            ) if k in data}
    except Exception:
        pass
    return None


# Minimum bars needed per window type to produce meaningful results
MIN_BARS = {'1M': 50, '2M': 80, '3M': 100, '4M': 120, '6M': 150,
            '1Y': 200, '2Y': 400, '3Y': 600}


def run_window_mining(strategy_id, window, n_trials=None):
    sid      = str(strategy_id)
    cfg      = STRATEGY_LIBRARY[sid]

    # Validate class exists before doing any heavy work
    cls_name = cfg['class']
    if not hasattr(strat_reg, cls_name):
        print(f"  [SKIP] Class '{cls_name}' not found in strategies module — fix settings.py")
        return None
    strat_cls = getattr(strat_reg, cls_name)

    start_date = window['start']
    end_date   = window['end']
    coin       = cfg['data']['coins']
    tf         = cfg['data']['timeframes']

    # Use window's own trial count unless caller overrides
    trials = n_trials if n_trials is not None else window.get('trials', 25)

    # 1. Load data first — skip window if bars too few for this timeframe
    df = load_data(coin, tf, start_date, end_date)
    min_bars = MIN_BARS.get(window['type'], 50)
    if df is None or df.empty or len(df) < min_bars:
        bars = len(df) if df is not None and not df.empty else 0
        print(f"  [SKIP] Only {bars} bars — need {min_bars} for {window['type']} window on {tf}")
        return None

    # 2. Regime + market features
    regime, regime_score   = classify_regime(start_date, end_date, coin=coin, timeframe=tf)
    market_features        = extract_market_features(start_date, end_date, coin=coin, timeframe=tf)

    # 3. Optimise for this window
    print(f"  Loaded {len(df):,} bars  ({start_date} → {end_date})")
    best_params, best_sharpe_opt, best_trial_num, actual_trials_run = optimize_window(
        df, strat_cls, cfg['params'], cfg['risk'], n_trials=trials
    )
    converged = actual_trials_run < trials  # True only if _EarlyStopping actually fired
    conv_tag  = f"converged @trial {best_trial_num}/{actual_trials_run} (of {trials})" if converged else f"used all {trials} trials"
    print(f"  Optimizer: best Sharpe {best_sharpe_opt:.3f}  [{conv_tag}]")

    # 4. Final verification run — capture equity curve + trades
    rm = RiskManager(
        risk_per_trade=cfg['risk']['risk_per_trade'],
        leverage=cfg['risk']['leverage'],
        trading_fee=cfg['risk']['trading_fee'],
    )
    engine = BacktestEngine(
        df, strat_cls(df, **best_params), rm,
        initial_balance=cfg['risk']['initial_balance']
    )
    equity = engine.run()
    m  = compute_metrics(equity, cfg['risk']['initial_balance'],
                         timestamps=engine.df.index, trades=engine.trades)
    nm = _extract_numeric(m)

    initial_bal = float(cfg['risk']['initial_balance'])
    final_bal   = float(equity[-1]) if equity else initial_bal

    # Helper: parse formatted metric strings like "$1,234.56" or "38.46%"
    def _parse_m(key, default=0.0):
        v = m.get(key, default)
        if v is None: return default
        s = str(v).replace('$', '').replace(',', '').replace('%', '').strip()
        try: return float(s)
        except (ValueError, TypeError): return default

    # Serialise raw trade events (timestamp → ISO string); accumulate fees + slippage
    trades_serializable = []
    total_fees_e     = 0.0
    total_slippage_e = 0.0
    for t in (engine.trades or []):
        t_copy = dict(t)
        if 'time' in t_copy and hasattr(t_copy['time'], 'isoformat'):
            t_copy['time'] = t_copy['time'].isoformat()
        trades_serializable.append(t_copy)
        total_fees_e     += float(t.get('fee', 0))
        total_slippage_e += float(t.get('slippage_usd', 0))

    # Pull win/loss/gross metrics from compute_metrics — uses net pnl (after entry fees)
    # and correct hedge-mode pairing, so values match the backtest dashboard exactly.
    wins_e         = int(m.get('Winning Trades', 0))
    losses_e       = int(m.get('Losing Trades', 0))
    gross_profit_e = _parse_m('Gross Profit')
    pf             = nm.get('Profit Factor', 0.0)
    gross_loss     = round(gross_profit_e / pf, 2) if 0 < pf < 99 else 0.0

    total_round_trips = wins_e + losses_e
    win_rate_pct      = float(nm.get('Win Rate', 0.0))

    # 5. Build full result (deep-dive + CSV summary)
    result = {
        "strategy_id":      sid,
        "category":         window.get('category', 'UNKNOWN'),
        "window_type":      window['type'],
        "start_date":       start_date,
        "end_date":         end_date,
        "regime":           regime,
        "regime_score":     regime_score,
        "market_features":  json.dumps(market_features),
        "roi":              round(float(nm.get('Total Return', 0)), 2),
        "sharpe":           round(float(nm.get('Sharpe Ratio', 0)), 3),
        "mdd":              round(float(nm.get('Max Drawdown %', 0)), 2),
        "trades":           total_round_trips,
        "profit_factor":    round(float(nm.get('Profit Factor', 0)), 2),
        "params":           json.dumps(best_params),
        "trials_budget":    trials,
        "best_trial_num":   best_trial_num,
        "converged":        converged,
        # Extended metrics — computed directly from engine (not via nm which lacks these keys)
        "initial_balance":  round(initial_bal, 2),
        "final_balance":    round(final_bal, 2),
        "net_profit":       round(final_bal - initial_bal, 2),
        "gross_profit":     round(gross_profit_e, 2),
        "gross_loss":       round(gross_loss, 2),
        "total_fees":       round(total_fees_e, 2),
        "total_slippage":   round(total_slippage_e, 4),
        "win_rate":         f"{win_rate_pct:.2f}%",
        "winning_trades":   wins_e,
        "losing_trades":    losses_e,
        "avg_duration_days": m.get('Avg Duration (days)', '0.0'),
        # Deep-dive only (not in CSV)
        "equity_curve":     [round(float(v), 2) for v in (equity or [])],
        "trades_detail":    trades_serializable,
    }

    # Save full result JSON
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(raw_result_path(sid, window), "w") as f:
        json.dump(result, f, indent=4)

    # Return CSV-safe summary
    return {k: result[k] for k in (
        "strategy_id", "category", "window_type", "start_date", "end_date",
        "regime", "regime_score", "roi", "sharpe", "mdd", "trades",
        "market_features", "params"
    )}


CSV_COLS = [
    "strategy_id", "category", "window_type", "start_date", "end_date",
    "regime", "regime_score", "roi", "sharpe", "mdd", "trades",
    "market_features", "params",
]


def merge_wisdom_matrix(new_results, strategy_id):
    """Replace rows for this strategy_id and save."""
    sid = str(strategy_id)
    if os.path.exists(WISDOM_PATH):
        existing = pd.read_csv(WISDOM_PATH)
        existing = existing[existing['strategy_id'].astype(str) != sid]
    else:
        existing = pd.DataFrame()

    new_df   = pd.DataFrame(new_results)
    combined = pd.concat([existing, new_df], ignore_index=True)
    # Enforce canonical column order; drop any stray extras
    ordered = [c for c in CSV_COLS if c in combined.columns]
    combined = combined[ordered]
    combined.to_csv(WISDOM_PATH, index=False)
    return len(combined)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy_id", required=True)
    parser.add_argument("--trials",     type=int, default=None,
                        help="Override trial count for all windows (default: use per-window spec)")
    parser.add_argument("--no_resume",  action="store_true",
                        help="Ignore cached results and re-run all windows")
    args = parser.parse_args()

    sid = str(args.strategy_id)
    if sid not in STRATEGY_LIBRARY:
        print(f"ERROR: Strategy ID {sid} not found in STRATEGY_LIBRARY.")
        sys.exit(1)

    with open("phase_7/data/generated_windows.json") as f:
        windows = json.load(f)

    total = len(windows)
    print(f"TOTAL_WINDOWS:{total}")
    print(f"Starting Pattern Mining — Strategy {sid} | {total} windows")

    results = []
    for i, window in enumerate(windows):
        pct = round((i + 1) / total * 100, 1)
        print(f"PROGRESS:{i+1}/{total}:{pct}:{window['category']}:{window['type']}:{window['start']}")
        sys.stdout.flush()

        if not args.no_resume:
            cached = load_existing_summary(sid, window)
            if cached:
                print(f"  (cached)")
                results.append(cached)
                continue

        print(f"  Mining {window['category']} {window['type']}  {window['start']} → {window['end']}  [{window.get('trials', 25)} trials]")
        sys.stdout.flush()
        res = run_window_mining(sid, window, n_trials=args.trials)
        if res:
            results.append(res)

    total_rows = merge_wisdom_matrix(results, sid)
    print(f"DONE:{len(results)}:{total_rows}")
    print(f"Mining complete. {len(results)} windows. Wisdom Matrix: {total_rows} total rows.")


if __name__ == "__main__":
    main()
