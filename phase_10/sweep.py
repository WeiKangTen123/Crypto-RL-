import os
import sys
import pandas as pd
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from phase_10 import engine

# Grid search parameters
TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d']
PAIRS = [('BNB', 'ADA'), ('BTC', 'ETH')]
DATE_FROM = '2023-01-01'
DATE_TO = '2026-05-31'

# TP/SL combinations
# (Entry Z, TP Z, SL Z)
RATIOS = [
    (2.5, 0.0, 3.0),   # Base Advanced (Risk 0.5, Reward 2.5) -> Ratio 1:5
    (2.0, 0.5, 2.5),   # Moderate (Risk 0.5, Reward 1.5) -> Ratio 1:3
    (2.5, 1.0, 3.5),   # Wider SL, Early TP (Risk 1.0, Reward 1.5) -> Ratio 1:1.5
    (3.0, 0.0, 3.5),   # Extreme Entry (Risk 0.5, Reward 3.0) -> Ratio 1:6
]

results = []

print("Starting Phase 10 Parameter Sweep...")
for tf in TIMEFRAMES:
    for entry_z, tp_z, sl_z in RATIOS:
        # Patch engine parameters dynamically
        engine.TIMEFRAME = tf
        engine.MIN_ENTRY_Z = entry_z
        engine.EXIT_ZSCORE = tp_z
        engine.Z_STOP_LOSS = sl_z
        engine.MAX_ENTRY_Z = sl_z - 0.1
        
        for coin_a, coin_b in PAIRS:
            try:
                r = engine.run_pair_backtest(
                    coin_a, coin_b, 
                    os.path.join(_ROOT, 'dataset'), 
                    DATE_FROM, DATE_TO, 
                    timeframe=tf, 
                    signal_timeframe=tf
                )
                
                results.append({
                    'Pair': f"{coin_a}-{coin_b}",
                    'TF': tf,
                    'Entry_Z': entry_z,
                    'TP_Z': tp_z,
                    'SL_Z': sl_z,
                    'ROI(%)': r.get('roi', 0),
                    'Sharpe': r.get('sharpe', 0),
                    'Trades': r.get('total_trades', 0),
                    'WinRate': r.get('win_rate', 0)
                })
            except Exception as e:
                pass

df = pd.DataFrame(results)
if not df.empty:
    df = df.sort_values(by='Sharpe', ascending=False)
    print("\nTop 15 Parameter Combinations by Sharpe Ratio:")
    print(df.head(15).to_string(index=False))
else:
    print("No results generated.")
