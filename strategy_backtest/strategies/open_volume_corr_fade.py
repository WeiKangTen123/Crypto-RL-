import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_open_vol_corr_fade

class OpenVolumeCorrFade(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Open-volume correlation fade (WorldQuant Alpha #6)
    Formula: -corr(open, vol, 10)
    
    A simpler version of the rank correlation factor. Relies on linear Pearson correlation.
    """
    
    SIGNAL_PARAMS = frozenset({'corr_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'corr_p': [5, 10, 20],
        'long_thresh': [0.5, 0.6, 0.7, 0.8],
        'short_thresh': [-0.8, -0.7, -0.6, -0.5],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, corr_p=10, long_thresh=0.6, short_thresh=-0.6, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.corr_p = int(corr_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_open_vol_corr_fade(df, corr_p=self.corr_p)
            
            # Simple momentum breakout logic based on the correlation
            long_cond = alpha > self.long_thresh
            short_cond = alpha < self.short_thresh
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            # Cross over logic to trigger entry
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
