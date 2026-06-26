import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from strategy_backtest.strategies.smc_order_block_reversal import SMCOrderBlockReversal

# Create dummy data
data = {
    'Open': [100, 102, 101, 103, 105, 104, 106, 107, 108, 107],
    'High': [101, 103, 102, 104, 106, 105, 107, 108, 109, 108],
    'Low': [99, 101, 100, 102, 104, 103, 105, 106, 107, 106],
    'Close': [100, 102, 101, 103, 105, 104, 106, 107, 108, 107],
    'Volume': [1000, 1100, 1050, 1200, 1300, 1250, 1400, 1500, 1600, 1550]
}
df = pd.DataFrame(data)

# Instantiate
strat = SMCOrderBlockReversal(df)

# Test generate_signals
res = strat.generate_signals()
print("Signals generated successfully:")
print(res[['High', 'Low', 'Close', 'signal']])

# Test manage_trade
row = res.iloc[0]
action, price = strat.manage_trade(row, 1.0, 100.0, 1000.0)
print(f"Manage trade result: {action}, {price}")
