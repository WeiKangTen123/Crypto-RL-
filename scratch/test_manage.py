import sys
import pandas as pd
sys.path.insert(0, '/Users/weikangten/Desktop/Crypto-RL')
from strategy_forge.composer.dna import StrategyDNA
from strategy_backtest.settings import STRATEGY_LIBRARY

cfg = STRATEGY_LIBRARY["120"]
df = pd.DataFrame({"Open": [1,2], "High": [2,3], "Low": [1,2], "Close": [2,3], "Volume": [10,20], "taker_buy_base_vol": [5,10]})
dna = StrategyDNA(df, entry=cfg["params"]["entry"], filters=cfg["params"].get("filters", []), exit_method=cfg["params"]["exit_method"], params=cfg["params"])
df_sig = dna.generate_signals()

row = df_sig.iloc[-1].copy()
row["_bars_held"] = 140 # max hold is 140
print(dna.manage_trade(row, 1, 2.0))
