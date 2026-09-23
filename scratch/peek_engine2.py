import sys
import os
ROOT = '/Users/weikangten/Desktop/Crypto-RL'
sys.path.insert(0, ROOT)
from strategy_backtest.run_backtest import load_data
from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager

sid = "120"
cfg = STRATEGY_LIBRARY[sid]
df = load_data(cfg['data']['coins'], cfg['data']['timeframes'], "2021-01-01", "2026-07-21", mode='portfolio')
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
equity = engine.run()

print("KEYS in df:", list(engine.df.columns))
print(engine.df[['Open', 'Close', 'signal']].head(10))
if hasattr(engine, '_positions'):
    print("_positions exists")
