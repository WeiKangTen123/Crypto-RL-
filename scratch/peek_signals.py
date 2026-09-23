import sys
import os
import pandas as pd
ROOT = '/Users/weikangten/Desktop/Crypto-RL'
sys.path.insert(0, ROOT)
from strategy_backtest.run_backtest import load_data
from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager

sid = "120"
cfg = STRATEGY_LIBRARY[sid]
coin = cfg['data']['coins']
df = load_data(coin, cfg['data']['timeframes'], "2021-01-01", "2026-07-21", mode='portfolio')
strat_cls = getattr(strategy_backtest.strategies, cfg['class'])
strategy = strat_cls(df, **cfg.get('params', {}))
rm = RiskManager(
    risk_per_trade=0.15,
    leverage=2.0,
    trading_fee=0.0004,
    maintenance_margin_rate=0.005,
    frequency=cfg['data']['timeframes'],
)
engine = BacktestEngine(df, strategy, rm, initial_balance=100000)
engine.run()

signals = []
df_times = list(df.index)
for t in engine.trades:
    exec_time = t['time']
    try:
        idx = df_times.index(exec_time)
        sig_time = df_times[idx - 1]
    except ValueError:
        sig_time = exec_time - pd.Timedelta(hours=4) # Fallback

    if t['type'] == 'BUY': tgt = 1
    elif t['type'] == 'SELL': tgt = -1
    elif t['type'] in ('EXIT_LONG', 'EXIT_SHORT'): tgt = 0
    else: continue

    signals.append({
        "ts": int(sig_time.value),
        "symbol": f"{coin}USDT" if "USDT" not in coin else coin,
        "target": tgt,
        "strength": 1.0,
        "margin": 100000,
        "leverage": 2.0,
        "notional": 200000
    })

print(f"Generated {len(signals)} signals!")
print("First 3:")
for s in signals[:3]: print(s)

