"""
run_backtest.py — run rule-based technical strategies inside the Crypto-RL system.

Uses the same parquet dataset as the DRL training pipeline so results are
directly comparable across strategies and DRL agents.

Usage
-----
# List all available strategies
python strategy_backtest/run_backtest.py --list

# Run a single strategy by ID
python strategy_backtest/run_backtest.py --strategy 1

# Run ALL strategies and compare
python strategy_backtest/run_backtest.py --strategy all

# Override date range
python strategy_backtest/run_backtest.py --strategy 3 --date_from 2023-01-01 --date_to 2026-01-01

# Save results to a CSV
python strategy_backtest/run_backtest.py --strategy all --save results/technical_backtest.csv
"""

import os
import sys
import argparse
import importlib
import pandas as pd
import numpy as np

# ── ensure Crypto-RL root is on the path ────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_FREQTRADE_PATH = os.path.join(_ROOT, 'freqtrade')
if _FREQTRADE_PATH not in sys.path:
    sys.path.insert(0, _FREQTRADE_PATH)

from strategy_backtest.settings  import STRATEGY_LIBRARY, DATASET_DIR
from strategy_backtest.engine    import BacktestEngine
from strategy_backtest.risk      import RiskManager
from strategy_backtest.metrics   import compute_metrics, _extract_numeric
from strategy_backtest.data_validator import DataValidator
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.portfolio_engine import PortfolioBacktestEngine
import strategy_backtest.strategies  # triggers auto-loader


# ── Data loader ──────────────────────────────────────────────────────────────

_COL_MAP = {
    'open':   'Open',
    'high':   'High',
    'low':    'Low',
    'close':  'Close',
    'volume': 'Volume',
}


def _safe_date(d, default):
    try:
        if not d or str(d).lower() == 'invalid-date':
            return default
        pd.Timestamp(d)
        return str(d)
    except Exception:
        return default


def load_data(coins, timeframe: str, date_from: str, date_to: str, mode='portfolio') -> pd.DataFrame:
    """
    Load OHLCV from Crypto-RL's shared parquet dataset.

    Args:
        coins: str or list
            - str (e.g., "BTCUSDT"): Single coin, backward compatible
            - list (e.g., ["BTCUSDT", "ETHUSDT"]): Multi-coin (portfolio mode only)
        timeframe: Bar frequency (1m, 5m, 15m, 30m, 1h, 4h, 1d)
        date_from, date_to: Date strings (ISO format)
        mode: 'portfolio' or 'per_coin'
            - 'portfolio': Concatenate all coins into one DF (default)
            - 'per_coin': Load separately (handled by caller in loop)

    Returns:
        DataFrame with columns: symbol*, Open, High, Low, Close, Volume, ...
        (* symbol column added only if multi-coin or mode='portfolio')

    Multi-Coin Notes:
        - When multi-coin: DF includes 'symbol' column for per-symbol keying
        - Bars are interleaved and sorted by time (all symbols at each timestamp)
        - Use in portfolio mode with state keying: self._ema[event.symbol]
        - Use in per_coin mode by loading each symbol separately
    """

    # Normalize coins to list
    if isinstance(coins, str):
        symbols = [coins]
        is_single_coin = True
    else:
        symbols = list(coins)
        is_single_coin = False

    # Sanitize dates
    d_from = _safe_date(date_from, '2021-01-01')
    d_to   = _safe_date(date_to,   '2026-12-31')

    dfs = []

    for symbol in symbols:
        path = os.path.join(DATASET_DIR, symbol, timeframe, 'spot_ohlcv.parquet')
        if not os.path.exists(path):
            print(f"  [WARN] Parquet not found: {path}")
            continue

        df = pd.read_parquet(path)
        df = df.rename(columns=_COL_MAP)

        # Parse and set datetime index
        if 'open_time' in df.columns:
            df['open_time'] = pd.to_datetime(df['open_time'])
            df = df.set_index('open_time')
        df = df.sort_index()

        # Date filter
        df = df[(df.index >= pd.Timestamp(d_from)) &
                (df.index <= pd.Timestamp(d_to))]

        # Keep OHLCV + order-flow extras
        cols_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
        for extra in ['taker_buy_base_vol', 'num_trades']:
            if extra in df.columns:
                cols_keep.append(extra)
        df = df[cols_keep]

        # Cast order-flow columns to numeric
        for extra in ['taker_buy_base_vol', 'num_trades']:
            if extra in df.columns:
                df[extra] = pd.to_numeric(df[extra], errors='coerce').fillna(0.0)

        # Drop unwanted columns
        for drop_col in ['symbol', 'interval', 'close_time', 'quote_asset_volume',
                         'taker_buy_quote_vol', 'ingested_at', 'tic']:
            if drop_col in df.columns:
                df = df.drop(columns=[drop_col])

        df = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])

        # Add symbol column if multi-coin
        if not is_single_coin:
            df['symbol'] = symbol

        # Merge funding_rate.parquet if exists
        fr_path = os.path.join(DATASET_DIR, symbol, timeframe, 'funding_rate.parquet')
        if os.path.exists(fr_path):
            try:
                fr = pd.read_parquet(fr_path)
                fr['open_time'] = pd.to_datetime(fr['open_time'])
                fr = fr.set_index('open_time').sort_index()
                fr = fr[(fr.index >= pd.Timestamp(d_from)) & (fr.index <= pd.Timestamp(d_to))]
                if 'funding_rate' in fr.columns:
                    df = df.join(fr[['funding_rate']], how='left')
                    df['funding_rate'] = df['funding_rate'].ffill().fillna(0.0)
            except Exception:
                pass

        # Merge order_book_depth.parquet if exists
        ob_path = os.path.join(DATASET_DIR, symbol, timeframe, 'order_book_depth.parquet')
        if os.path.exists(ob_path):
            try:
                ob = pd.read_parquet(ob_path)
                ob['timestamp'] = pd.to_datetime(ob['timestamp'])
                ob = ob.set_index('timestamp').sort_index()
                ob = ob[(ob.index >= pd.Timestamp(d_from)) & (ob.index <= pd.Timestamp(d_to))]

                ob_cols = [c for c in ob.columns if c.startswith('depth_') or c.startswith('notional_')]
                if ob_cols:
                    df = df.join(ob[ob_cols], how='left')
                    df[ob_cols] = df[ob_cols].ffill().fillna(0.0)
            except Exception:
                pass

        dfs.append(df)
        print(f"  Loaded {symbol}: {len(df):,} bars  ({df.index[0].date()} → {df.index[-1].date()})")

    if not dfs:
        raise ValueError(f"No data loaded for symbols: {symbols}")

    if not is_single_coin:
        df_dict = {sym: df for sym, df in zip(symbols, dfs)}
        print(f"  Loaded {len(symbols)} symbols as dictionary.")
        
        # Validate each symbol's data separately
        for sym, sym_data in df_dict.items():
            validator = DataValidator(strict=False)
            issues = validator.validate(sym_data, symbol=sym)
            validator.print_summary()

        return df_dict
    else:
        print(f"  Total: {len(dfs[0]):,} bars")

        # Validate single-coin data
        validator = DataValidator(strict=False)
        issues = validator.validate(dfs[0], symbol=symbols[0])
        validator.print_summary()

        return dfs[0]


# ── Strategy runner ───────────────────────────────────────────────────────────

def run_strategy(cfg: dict, date_from: str = None, date_to: str = None, mode: str = 'portfolio') -> dict:
    """
    Run a single strategy config and return metrics dict.

    Args:
        cfg: Strategy config dict
        date_from, date_to: Optional date overrides
        mode: 'portfolio' (all coins in one run) or 'per_coin' (separate runs per coin)

    Returns:
        metrics dict with equity, trades, sharpe, etc.

    Notes:
        - Portfolio mode: All symbols share one equity book; strategy must key state by symbol
        - Per-coin mode: Called once per symbol; each symbol runs isolated
    """

    data_cfg = cfg['data']
    risk_cfg = cfg['risk']
    params   = cfg.get('params', {})

    d_from = date_from or data_cfg['date_from']
    d_to   = date_to   or data_cfg['date_to']

    # Get coins/symbols
    coins = data_cfg.get('coins', data_cfg.get('symbols', 'BTC'))  # Backward compat
    is_multi_coin = isinstance(coins, list) and len(coins) > 1

    print(f"\n{'='*60}")
    print(f"  Strategy : {cfg['id']}")
    print(f"  Desc     : {cfg['desc']}")
    print(f"  Class    : {cfg['class']}   | TF: {data_cfg['timeframes']}")
    if is_multi_coin:
        print(f"  Symbols  : {coins}  | Mode: {mode}")
    else:
        coin_str = coins[0] if isinstance(coins, list) else coins
        print(f"  Coin     : {coin_str}")
    print(f"  Period   : {d_from} → {d_to}")
    print(f"{'='*60}")

    # Load data (multi-coin if applicable)
    df = load_data(coins, data_cfg['timeframes'], d_from, d_to, mode=mode)
    
    is_empty = False
    if isinstance(df, dict):
        if not df or all(d.empty for d in df.values()):
            is_empty = True
    elif df.empty:
        is_empty = True
        
    if is_empty:
        print("  [SKIP] No data in requested range.")
        return {}

    # Warn if single-coin strategy with multi-coin data in portfolio mode
    if is_multi_coin and mode == 'portfolio':
        print("  [INFO] Multi-coin data loaded in portfolio mode. Using PortfolioBacktestEngine.")

    # Resolve strategy class from auto-loaded strategies module
    strat_cls = getattr(strategy_backtest.strategies, cfg['class'], None)
    if strat_cls is None:
        print(f"  [ERROR] Strategy class '{cfg['class']}' not found.")
        return {}

    # Build strategy + engine
    try:
        strategy = strat_cls(df, **params)

        # Frequency-based risk defaults (SignalHive standard)
        frequency = data_cfg['timeframes'] if 'timeframes' in data_cfg else None
        risk_per_trade = risk_cfg.get('risk_per_trade')
        if risk_per_trade is None and frequency:
            # Auto-set per-frequency default
            risk_per_trade = RiskManager.FREQUENCY_DEFAULTS.get(frequency, 0.15)
            print(f"  [INFO] Risk per trade auto-set to {risk_per_trade:.1%} (frequency={frequency})")

        rm = RiskManager(
            risk_per_trade=risk_per_trade or risk_cfg.get('risk_per_trade', 0.15),
            leverage=risk_cfg['leverage'],
            trading_fee=risk_cfg['trading_fee'],
            slippage_pct=0.0,  # DEPRECATED — use CostCalculator for realistic slippage
            maintenance_margin_rate=risk_cfg['maintenance_margin_rate'],
            frequency=frequency,
        )
        if is_multi_coin and mode == 'portfolio':
            if not issubclass(strat_cls, MultiCoinBaseStrategy):
                raise TypeError(f"Strategy {cfg['class']} must inherit from MultiCoinBaseStrategy for portfolio mode.")
            engine = PortfolioBacktestEngine(df, strategy, rm, initial_balance=risk_cfg['initial_balance'])
        else:
            engine = BacktestEngine(df, strategy, rm, initial_balance=risk_cfg['initial_balance'])
        equity_curve = engine.run()
    except Exception as e:
        print(f"  [ERROR] Strategy {cfg['id']} failed: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'strategy_id': cfg['id']}

    if not equity_curve:
        print("  [SKIP] Engine returned empty equity curve.")
        return {'error': 'empty equity curve', 'strategy_id': cfg['id']}

    # Compute metrics (with all-in costs: fees + slippage + borrow + funding)
    m = compute_metrics(
        equity=equity_curve,
        initial_balance=risk_cfg['initial_balance'],
        timestamps=engine._times if hasattr(engine, '_times') else engine.df.index,
        trades=engine.trades,
        total_slippage=engine.total_slippage,
    )

    _print_metrics(cfg['id'], m)
    _print_position_size(engine.trades)
    num = _extract_numeric(m)
    num['strategy_id'] = cfg['id']
    num['class']       = cfg['class']
    num['timeframe']   = data_cfg['timeframes']
    num['coin']        = data_cfg['coins']
    return num


# ── Output helpers ────────────────────────────────────────────────────────────

def _print_metrics(name: str, m: dict):
    print(f"\n  ── Results: {name} ──")
    key_order = [
        "Total Return", "Annual Return", "Sharpe Ratio", "Sortino Ratio",
        "Calmar Ratio", "Max Drawdown (%)", "Profit Factor", "Win Rate",
        "Total Trades", "Expectancy",
    ]
    for k in key_order:
        if k in m:
            print(f"    {k:<22}: {m[k]}")

    if "YEARLY_RETURNS" in m:
        print("\n  ── Yearly Returns ──")
        for yr, v in sorted(m["YEARLY_RETURNS"].items()):
            print(f"    {yr}  {v['return']:>10}   fees {v['fees']}")


def _print_position_size(trades: list):
    entries = [t for t in (trades or []) if t.get('type') in ('BUY', 'SELL', 'BUY_ADD', 'SELL_ADD')]
    if not entries:
        return
    qtys = [float(t['qty']) for t in entries if t.get('qty')]
    ntls = [float(t['notional']) for t in entries if t.get('notional')]
    if qtys:
        print(f"    {'Avg Qty / Trade':<22}: {sum(qtys)/len(qtys):.4f} units  "
              f"(min {min(qtys):.4f} / max {max(qtys):.4f})")
    if ntls:
        print(f"    {'Avg Notional':<22}: ${sum(ntls)/len(ntls):,.2f}  "
              f"(min ${min(ntls):,.2f} / max ${max(ntls):,.2f})")


def _print_comparison_table(rows: list):
    if not rows:
        return
    df = pd.DataFrame(rows).set_index('strategy_id')
    cols = ['coin', 'timeframe', 'class', 'Total Return', 'Annual Return',
            'Sharpe Ratio', 'Max Drawdown %', 'Win Rate', 'Total Trades', 'Profit Factor']
    cols = [c for c in cols if c in df.columns]
    df = df[cols].sort_values('Sharpe Ratio', ascending=False)

    print("\n" + "="*100)
    print("  STRATEGY COMPARISON TABLE  (sorted by Sharpe Ratio)")
    print("="*100)
    print(df.to_string())
    print("="*100)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Crypto-RL Technical Strategy Backtest')
    parser.add_argument('--strategy',  default='list',
                        help='Strategy ID (e.g. 1, 3, 13) or "all" to run everything. '
                             'Use "list" to show available strategies.')
    parser.add_argument('--date_from', default=None, help='Override start date (YYYY-MM-DD)')
    parser.add_argument('--date_to',   default=None, help='Override end date (YYYY-MM-DD)')
    parser.add_argument('--save',      default=None,
                        help='Save comparison CSV to this path (e.g. results/tech_backtest.csv)')
    args = parser.parse_args()

    # ── List mode ──
    if args.strategy.lower() in ('list', '--list'):
        print("\nAvailable strategies:")
        print(f"  {'ID':<5} {'Coin':<6} {'TF':<6} {'Class':<40} {'Description'}")
        print(f"  {'-'*5} {'-'*6} {'-'*6} {'-'*40} {'-'*40}")
        for sid, cfg in sorted(STRATEGY_LIBRARY.items(), key=lambda x: int(x[0].split('_')[0]) if x[0].split('_')[0].isdigit() else 9999):
            d = cfg['data']
            print(f"  {sid:<5} {d['coins']:<6} {d['timeframes']:<6} {cfg['class']:<40} {cfg['desc']}")
        return

    # ── Run mode ──
    if args.strategy.lower() == 'all':
        ids_to_run = sorted(STRATEGY_LIBRARY.keys(),
                            key=lambda x: (0, int(x.split('_')[0])) if x.split('_')[0].isdigit() else (1, x))
    else:
        ids_to_run = [args.strategy]

    results = []
    for sid in ids_to_run:
        if sid not in STRATEGY_LIBRARY:
            print(f"[WARN] Unknown strategy ID: {sid}. Use --strategy list to see available IDs.")
            continue
        try:
            r = run_strategy(STRATEGY_LIBRARY[sid], args.date_from, args.date_to)
            if r:
                results.append(r)
        except Exception as e:
            print(f"  [ERROR] Strategy {sid} failed: {e}")
            import traceback; traceback.print_exc()

    if len(results) > 1:
        _print_comparison_table(results)

    if args.save and results:
        out_path = os.path.join(_ROOT, args.save)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        pd.DataFrame(results).to_csv(out_path, index=False)
        print(f"\nResults saved to: {out_path}")

        # ── Auto-Sync to Obsidian ──
        try:
            from utility.sync_backtest_to_obsidian import main as sync_obsidian
            print("Syncing results to Obsidian Factor Library...")
            sync_obsidian()
        except ImportError:
            print("[WARN] Could not import utility.sync_backtest_to_obsidian. Skipping sync.")
        except Exception as e:
            print(f"[ERROR] Obsidian sync failed: {e}")


if __name__ == '__main__':
    main()
