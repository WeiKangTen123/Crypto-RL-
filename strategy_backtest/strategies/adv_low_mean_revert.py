import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_adv_low_mean_revert

class AdvLowMeanRevert(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Adv-low mean-revert + close (WorldQuant Alpha #28).
    Formula: correlation(adv20, low, 5) + ((high + low) / 2) - close
    """
    
    SIGNAL_PARAMS = frozenset({'adv_p', 'corr_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'adv_p': [10, 20, 40],
        'corr_p': [3, 5, 10],
        'long_thresh': [0.1, 0.5, 1.0],
        'short_thresh': [-1.0, -0.5, -0.1],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, adv_p=20, corr_p=5, long_thresh=0.5, short_thresh=-0.5, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.adv_p = int(adv_p)
        self.corr_p = int(corr_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_adv_low_mean_revert(df, adv_p=self.adv_p, corr_p=self.corr_p)
            
            # Since the formula contains the difference between the median price and close price,
            # higher values mean the close is relatively low compared to the bar's midpoint 
            # and the volume-low correlation. This suggests a long setup.
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
