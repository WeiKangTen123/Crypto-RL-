import traceback
from strategy_backtest.strategies.td_vsb_strategy import TDVSBStrategy
from strategy_backtest.strategies.zve_strategy import ZVEStrategy
from strategy_backtest.run_backtest import load_data

try:
    df = load_data('BTC', '1h', '2023-01-01', '2026-06-01')
    s = TDVSBStrategy(df)
    s.generate_signals()
except Exception:
    traceback.print_exc()

print("---")

try:
    s2 = ZVEStrategy(df)
    s2.generate_signals()
except Exception:
    traceback.print_exc()
