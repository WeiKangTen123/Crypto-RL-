import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_ts_rank

class LowRankMeanReversion(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Low rank mean-reversion (WorldQuant Alpha #4 adaptation)
    Formula: -ts_rank(low, ts_period)
    
    This is a pure time-series mean-reversion factor.
    If the current low is the lowest in the recent window, its ts_rank is near 0,
    so alpha (-ts_rank) is near 0. We want to buy oversold, so if alpha > -0.2, we Long.
    If the current low is the highest in the recent window, its ts_rank is near 1,
    so alpha is near -1. We want to sell overbought, so if alpha < -0.8, we Short.
    """
    
    SIGNAL_PARAMS = frozenset({'ts_period', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'ts_period': [5, 9, 14, 21],
        'long_thresh': [-0.2, -0.3, -0.4],
        'short_thresh': [-0.8, -0.7, -0.6],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, ts_period=9, long_thresh=-0.2, short_thresh=-0.8, sl_pct=0.05, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.ts_period = int(ts_period)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            # ts_rank ranges from 0 to 1.
            # alpha ranges from -1 to 0.
            alpha = -calc_ts_rank(df['Low'], period=self.ts_period)
            
            # Simple mean-reversion logic
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
