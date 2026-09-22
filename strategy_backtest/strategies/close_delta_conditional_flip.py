import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_close_delta_conditional_flip

class CloseDeltaConditionalFlip(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Close delta conditional flip (WorldQuant Alpha #9)
    Formula: ((ts_min(delta(close, 1), 5) > 0) ? delta(close, 1) : 
             ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))
             
    This strategy essentially trades the momentum (delta) if we are in a pure up-trend (min > 0)
    or pure down-trend (max < 0). Otherwise, it fades the momentum (mean reversion).
    """
    
    SIGNAL_PARAMS = frozenset({'delta_p', 'ts_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'delta_p': [1, 2, 3],
        'ts_p': [3, 5, 8],
        'long_thresh': [0, 0.01, 0.02, 0.03],
        'short_thresh': [-0.03, -0.02, -0.01, 0],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, delta_p=1, ts_p=5, long_thresh=0.01, short_thresh=-0.01, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.delta_p = int(delta_p)
        self.ts_p = int(ts_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            # alpha is in raw price terms (or returns if we use log close, but here it's raw price diff)
            # To normalize, we should probably divide by close price
            alpha = calc_close_delta_conditional_flip(df, delta_p=self.delta_p, ts_p=self.ts_p)
            alpha_pct = alpha / df['Close']
            
            long_cond = alpha_pct > self.long_thresh
            short_cond = alpha_pct < self.short_thresh
            
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
