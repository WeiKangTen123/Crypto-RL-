
import os
import sys
import pandas as pd

# ── ensure Crypto-RL root is on the path ────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from strategy_backtest.run_backtest import run_strategy, _print_comparison_table

COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
TIMEFRAMES = ['15m', '30m', '1h', '4h']

# Baseline parameters from Strategy ID 10
TIP_PARAMS = {
    "bb_period": 50,
    "bb_std": 1.5,
    "intensity_period": 48,
    "intensity_std": 2.5,
    "taker_ratio_threshold": 0.53,
    "max_hold_bars": 24
}

def main():
    results = []
    
    for coin in COINS:
        for tf in TIMEFRAMES:
            path = os.path.join(_ROOT, 'dataset', coin, tf, 'spot_ohlcv.parquet')
            if not os.path.exists(path):
                print(f"[SKIP] Data not found for {coin} {tf}")
                continue
            
            cfg = {
                "id": f"TIP_{coin}_{tf}",
                "desc": f"TIP Breakout Sweep {coin} {tf}",
                "class": "TIPBreakoutStrategy",
                "data": {"coins": coin, "timeframes": tf, "date_from": "2021-01-01", "date_to": "2026-05-31"},
                "risk": {
                    "initial_balance": 1000,
                    "risk_per_trade": 0.1,
                    "leverage": 10,
                    "trading_fee": 0.0005,
                    "maintenance_margin_rate": 0.005
                },
                "params": TIP_PARAMS
            }
            
            try:
                print(f"\n>>> Running TIP Breakout on {coin} {tf}...")
                res = run_strategy(cfg)
                if res and 'error' not in res:
                    results.append(res)
            except Exception as e:
                print(f"[ERROR] Failed {coin} {tf}: {e}")
    
    if results:
        _print_comparison_table(results)
        
        # Save to a specialized CSV
        out_path = os.path.join(_ROOT, 'results', 'tip_breakout_global_sweep.csv')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        pd.DataFrame(results).to_csv(out_path, index=False)
        print(f"\nGlobal sweep results saved to: {out_path}")

if __name__ == '__main__':
    main()
