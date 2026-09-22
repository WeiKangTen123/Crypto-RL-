import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_close_return_cond_gap

class CloseReturnCondGap(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Close-return conditional gap (WorldQuant Alpha #19 adaptation).
    Formula: ((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank(1 + sum(returns, 250))))
    Simplifies to: -sign(delta(close, 7)) * (1 + rank(sum(returns, 250)))
    """
    
    SIGNAL_PARAMS = frozenset({'delta_p', 'sum_p', 'rank_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'delta_p': [3, 7, 14],
        'sum_p': [20, 60, 120],
        'rank_p': [5, 10, 20],
        'long_thresh': [0.2, 0.5, 0.8],
        'short_thresh': [-0.8, -0.5, -0.2],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, delta_p=7, sum_p=60, rank_p=10, long_thresh=0.5, short_thresh=-0.5, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.delta_p = int(delta_p)
        self.sum_p = int(sum_p)
        self.rank_p = int(rank_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_close_return_cond_gap(df, delta_p=self.delta_p, sum_p=self.sum_p, rank_p=self.rank_p)
            
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
