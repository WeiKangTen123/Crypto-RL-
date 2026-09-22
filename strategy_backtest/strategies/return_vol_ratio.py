import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_return_vol_ratio

class ReturnVolRatio(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Return Vol Ratio + Close Delta (WorldQuant Alpha #34).
    Formula: rank(stddev(returns, 2) / stddev(returns, 5)) - rank(delta(close, 1))
    """
    
    SIGNAL_PARAMS = frozenset({'short_vol_p', 'long_vol_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'short_vol_p': [2, 3, 5, 8, 10],
        'long_vol_p': [10, 20, 30, 50, 100],
        'long_thresh': [0.2, 0.4, 0.6, 0.8, 0.9],
        'short_thresh': [-0.9, -0.8, -0.6, -0.4, -0.2],
        'sl_pct': [0.01, 0.03, 0.05, 0.10, 0.15],
        'tp_pct': [0.02, 0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, short_vol_p=2, long_vol_p=5, long_thresh=0.6, short_thresh=-0.6, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.short_vol_p = int(short_vol_p)
        self.long_vol_p = int(long_vol_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_return_vol_ratio(df, short_vol_p=self.short_vol_p, long_vol_p=self.long_vol_p)
            
            # Alpha bounds between -1 and 1
            long_cond = alpha > self.long_thresh
            short_cond = alpha < self.short_thresh
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            signal_diff = np.diff(signal, prepend=0)
            entry_signals = np.zeros(len(df), dtype=int)
            entry_signals[(signal == 1) & (signal_diff > 0)] = 1
            entry_signals[(signal == -1) & (signal_diff < 0)] = -1
            
            self.dfs[sym]['signal'] = entry_signals
            
        return self.dfs

    def manage_trade(self, symbol: str, bar, qty: float, entry_price: float, entry_balance: float):
        action, exec_price = 'HOLD', None
        side = 1 if qty > 0 else -1
        
        if side == 1:
            sl_price = entry_price * (1 - self.sl_pct)
            tp_price = entry_price * (1 + self.tp_pct)
            
            if bar.Low <= sl_price:
                action, exec_price = 'SL', sl_price
            elif bar.High >= tp_price:
                action, exec_price = 'TP', tp_price
                
        else:
            sl_price = entry_price * (1 + self.sl_pct)
            tp_price = entry_price * (1 - self.tp_pct)
            
            if bar.High >= sl_price:
                action, exec_price = 'SL', sl_price
            elif bar.Low <= tp_price:
                action, exec_price = 'TP', tp_price
                
        return action, exec_price
