import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_vol_close_anti_mom

class VolCloseAntiMom(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Volume-close anti-momentum (WorldQuant Alpha #12 adaptation).
    Formula: sign(delta(volume, 1)) * (-1 * delta(close, 1))
    """
    
    SIGNAL_PARAMS = frozenset({'delta_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'delta_p': [1, 3, 5],
        'long_thresh': [5.0, 20.0, 50.0],
        'short_thresh': [-50.0, -20.0, -5.0],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, delta_p=1, long_thresh=20.0, short_thresh=-20.0, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.delta_p = int(delta_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_vol_close_anti_mom(df, delta_p=self.delta_p)
            
            # Since the formula contains the raw dollar difference in close price,
            # the thresholds will trigger when the price makes a large move accompanied by volume changes.
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
