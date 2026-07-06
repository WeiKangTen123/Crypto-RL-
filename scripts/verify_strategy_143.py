import os
import sys
import json
import copy

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies as strat_reg
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager
from strategy_backtest.metrics import compute_metrics, _extract_numeric
from strategy_backtest.run_backtest import load_data

def run_single_backtest(coin, tf, date_from, date_to, params, cfg):
    df = load_data(coin, tf, date_from, date_to)
    if df is None or df.empty or len(df) < 50:
        raise ValueError("Insufficient data")
    
    strat_cls = getattr(strat_reg, cfg['class'])
    rm = RiskManager(
        risk_per_trade=cfg['risk']['risk_per_trade'],
        leverage=cfg['risk']['leverage'],
        trading_fee=cfg['risk']['trading_fee'],
        slippage_pct=cfg['risk'].get('slippage_pct', 0.0005),
        maintenance_margin_rate=cfg['risk']['maintenance_margin_rate'],
    )
    engine = BacktestEngine(
        df, strat_cls(df, **params), rm,
        initial_balance=cfg['risk']['initial_balance']
    )
    equity = engine.run()
    m = compute_metrics(equity, cfg['risk']['initial_balance'], timestamps=engine.df.index, trades=engine.trades)
    return _extract_numeric(m)

def main():
    cfg = STRATEGY_LIBRARY['143']
    params = cfg['params']
    date_from = cfg['data'].get('date_from') or '2021-01-01'
    date_to = cfg['data'].get('date_to') or '2026-05-31'
    tf = cfg['data']['timeframes']
    primary_coin = cfg['data']['coins']

    print(f"--- VERIFYING STRATEGY 143 ({cfg['class']}) ---")
    print(f"Primary Asset: {primary_coin} / {tf}")
    print(f"Date Range: {date_from} -> {date_to}")
    print(f"Parameters: {params}\n")

    # 1. Primary Backtest
    print("Running primary backtest...")
    primary_results = run_single_backtest(primary_coin, tf, date_from, date_to, params, cfg)
    p_sharpe = primary_results.get('Sharpe Ratio', 0.0)
    print(f"Primary Sharpe: {p_sharpe:.3f}")
    print(f"Primary Trades: {int(primary_results.get('Total Trades', 0))}")
    print(f"Primary Return: {primary_results.get('Total Return', 0.0):.1f}%")
    print(f"Primary MDD: {primary_results.get('Max Drawdown %', 0.0):.1f}%\n")

    # 2. Cross-Asset Stress Test
    cross_assets = ['ETH', 'BTC']
    cross_results = {}
    for coin in cross_assets:
        print(f"Running cross-asset test on {coin}...")
        try:
            res = run_single_backtest(coin, tf, date_from, date_to, params, cfg)
            cross_results[coin] = res
            print(f"  {coin} Sharpe: {res.get('Sharpe Ratio', 0.0):.3f} | Trades: {int(res.get('Total Trades', 0))} | Return: {res.get('Total Return', 0.0):.1f}%")
        except Exception as e:
            print(f"  Failed on {coin}: {e}")

    # 3. Parameter Stability Test (+/-10% parameter shifts)
    # Target numerical parameters
    tunable_keys = ['vrsi_period', 'vrsi_oversold', 'vrsi_overbought', 'vwap_period', 'vwap_std_mult', 'sl_pct', 'ema_period']
    print("\nRunning Parameter Stability Test (+/- 10% perturbations)...")
    stability_passed = True
    stability_runs = []
    
    # We will test +/-10% for numerical params
    for pk in tunable_keys:
        val = params.get(pk)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            for factor in [0.9, 1.1]:
                test_params = copy.deepcopy(params)
                test_val = val * factor
                if isinstance(val, int):
                    test_val = int(round(test_val))
                test_params[pk] = test_val
                
                try:
                    res = run_single_backtest(primary_coin, tf, date_from, date_to, test_params, cfg)
                    s_sharpe = res.get('Sharpe Ratio', 0.0)
                    drop = p_sharpe - s_sharpe
                    stability_runs.append((pk, test_val, s_sharpe))
                    print(f"  Varying {pk} -> {test_val:.4f}: Sharpe = {s_sharpe:.3f}")
                    if s_sharpe < 0.0 or (p_sharpe > 0 and s_sharpe < 0.5 * p_sharpe):
                        print(f"    WARNING: Significant performance drop/crash on {pk} perturbation!")
                        stability_passed = False
                except Exception as e:
                    print(f"    Crash when varying {pk}: {e}")
                    stability_passed = False

    # Save results to a validation file
    validation_output = {
        "strategy_id": "143",
        "primary_results": {
            "sharpe": p_sharpe,
            "return": primary_results.get('Total Return', 0.0),
            "mdd": primary_results.get('Max Drawdown %', 0.0),
            "trades": int(primary_results.get('Total Trades', 0)),
            "win_rate": primary_results.get('Win Rate', 0.0),
            "profit_factor": primary_results.get('Profit Factor', 0.0)
        },
        "cross_asset_results": {
            coin: {
                "sharpe": res.get('Sharpe Ratio', 0.0),
                "return": res.get('Total Return', 0.0),
                "mdd": res.get('Max Drawdown %', 0.0),
                "trades": int(res.get('Total Trades', 0))
            } for coin, res in cross_results.items()
        },
        "stability_passed": stability_passed,
        "stability_runs": stability_runs
    }
    
    val_file = ".gemini/skills/crypto-strategy-tuner/data/strategy_143_validation.json"
    with open(val_file, 'w') as f:
        json.dump(validation_output, f, indent=2)
    print(f"\nSaved validation results to {val_file}")

if __name__ == "__main__":
    main()
