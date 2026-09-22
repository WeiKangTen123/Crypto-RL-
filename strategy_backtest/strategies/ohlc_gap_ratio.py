import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_ohlc_gap_ratio

class OhlcGapRatio(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: OHLC gap ratio (WorldQuant Alpha #101).
    Formula: (close - open) / (high - low + 0.001)
    """
    
    SIGNAL_PARAMS = frozenset({'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'long_thresh': [0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
        'short_thresh': [-0.95, -0.9, -0.7, -0.5, -0.3, -0.1],
        'sl_pct': [0.01, 0.03, 0.05, 0.10, 0.15],
        'tp_pct': [0.02, 0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, long_thresh=0.7, short_thresh=-0.7, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_ohlc_gap_ratio(df)
            
            # The gap ratio natively bounds itself between -1 and 1 
            # A value near 1 means it closed on the absolute high and opened on the low (extreme bullish)
            # A value near -1 means it closed on the absolute low and opened on the high (extreme bearish)
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
