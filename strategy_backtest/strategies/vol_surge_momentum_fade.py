import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_vol_surge_momentum_fade

class VolSurgeMomentumFade(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Volume surge momentum fade (WorldQuant Alpha #7)
    Formula: (adv20 < vol) ? -ts_rank(abs(delta(close, 7)), 60) * sign(delta(close, 7)) : -1
    
    If volume surges above moving average, alpha is negative if price went up, and positive if price went down.
    We long when alpha > threshold, and short when < -threshold.
    """
    
    SIGNAL_PARAMS = frozenset({'sma_p', 'delta_p', 'ts_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'sma_p': [10, 20, 30],
        'delta_p': [3, 7, 10],
        'ts_p': [30, 60, 90],
        'long_thresh': [0.5, 0.6, 0.7, 0.8],
        'short_thresh': [-0.8, -0.7, -0.6, -0.5],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, sma_p=20, delta_p=7, ts_p=60, long_thresh=0.6, short_thresh=-0.6, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.sma_p = int(sma_p)
        self.delta_p = int(delta_p)
        self.ts_p = int(ts_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_vol_surge_momentum_fade(df, sma_p=self.sma_p, delta_p=self.delta_p, ts_p=self.ts_p)
            
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
