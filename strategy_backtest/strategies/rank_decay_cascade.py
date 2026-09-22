import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear

class RankDecayCascade(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Rank Decay Cascade (WorldQuant Alpha #31).
    Formula: rank(decay_linear(-1 * rank(delta(close, 10)), 10)) + rank(-1 * delta(close, 3))
    
    This "HARD" factor is a multi-timeframe mean-reversion cascade.
    1. It calculates the cross-sectional rank of the 10-period momentum and fades it (-1).
    2. It applies a 10-period linear decay to this fade, heavily weighting recent momentum drops.
    3. It ranks this decayed fade, and adds it to the rank of the 3-period momentum fade.
    4. By summing two separate mean-reversion ranks (one heavily smoothed, one raw and short), 
       it creates a robust score between 0.0 and 2.0, hunting for coins that are deeply 
       oversold on multiple timeframes simultaneously.
    """
    
    SIGNAL_PARAMS = frozenset({'long_delta_p', 'decay_p', 'short_delta_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'long_delta_p': [5, 10, 15, 20],
        'decay_p': [5, 10, 15, 20],
        'short_delta_p': [2, 3, 5, 7],
        'long_thresh': [1.2, 1.4, 1.6, 1.8, 1.9],
        'short_thresh': [0.1, 0.2, 0.4, 0.6, 0.8],
        'sl_pct': [0.03, 0.05, 0.10, 0.15],
        'tp_pct': [0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, long_delta_p=10, decay_p=10, short_delta_p=3, long_thresh=1.5, short_thresh=0.5, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.long_delta_p = int(long_delta_p)
        self.decay_p = int(decay_p)
        self.short_delta_p = int(short_delta_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        
        # delta(close, 10)
        long_delta = close_df.diff(self.long_delta_p)
        
        # -1 * rank(long_delta)
        long_rank_fade = -1.0 * long_delta.rank(axis=1, pct=True)
        
        # decay_linear(fade, 10)
        decayed_fade = calc_decay_linear(long_rank_fade, self.decay_p)
        
        # rank(decayed)
        part1 = decayed_fade.rank(axis=1, pct=True)
        
        # -1 * delta(close, 3)
        short_delta_fade = -1.0 * close_df.diff(self.short_delta_p)
        
        # rank(short_fade)
        part2 = short_delta_fade.rank(axis=1, pct=True)
        
        # Final Alpha (between 0.0 and 2.0)
        raw_alpha = part1 + part2
        
        for sym, df in self.dfs.items():
            alpha = raw_alpha[sym].loc[df.index]
            
            long_cond = alpha > self.long_thresh
            short_cond = alpha < self.short_thresh
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond.fillna(False)] = 1
            signal[short_cond.fillna(False)] = -1
            
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
