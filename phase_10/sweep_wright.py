import os
import sys
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from phase_10 import wright_engine as engine

# Grid search parameters
TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d']
PAIRS = [('BNB', 'ADA'), ('BTC', 'ETH'), ('XRP', 'ADA')]
DATE_FROM = '2023-01-01'
DATE_TO = '2026-05-31'

# Test various combinations of (Entry_Z, TP_Z, SL_Z)
RATIOS = [
    (1.5, 0.5, 2.0),   # Early Stop, Short TP
    (1.5, 0.0, 2.5),   # Medium Stop, Full Reversion TP
    (2.0, 0.0, 3.0),   # Wider Entry, Standard Stop
    (2.0, 1.0, 2.5),   # Wider Entry, Early TP, Tight Stop
    (2.5, 0.0, 3.5),   # Extreme Entry, Wide Stop
    (2.5, 1.0, 3.0),   # Extreme Entry, Early TP
    (3.0, 0.0, 4.0),   # Very Extreme Entry
]

results = []

print("Starting FULL Phase 10 Parameter Sweep for WRIGHT ENGINE (Clean)...")
for tf in TIMEFRAMES:
    for entry_z, tp_z, sl_z in RATIOS:
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
                    'Entry': entry_z,
                    'TP': tp_z,
                    'SL': sl_z,
                    'ROI(%)': round(r.get('roi', 0), 2),
                    'Sharpe': round(r.get('sharpe', 0), 3),
                    'Trades': r.get('total_trades', 0),
                    'WinRate': round(r.get('win_rate', 0), 1)
                })
            except Exception as e:
                pass

df = pd.DataFrame(results)
if not df.empty:
    df = df.sort_values(by='Sharpe', ascending=False)
    print("\nTop 15 Wright (Clean) Parameter Combinations:")
    print(df.head(15).to_string(index=False))
else:
    print("No results generated.")
