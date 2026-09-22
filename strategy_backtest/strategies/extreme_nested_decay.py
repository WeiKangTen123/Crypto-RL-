import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear

class ExtremeNestedDecay(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Extreme Nested Rank Decay (WorldQuant Alpha #29).
    Simplified Formula: min(rank(log(ts_min(rank(-rank(delta(close, 5))), 2))), rank(decay_linear(rank(-returns), 5)))
    
    This "HARD" factor is an aggressive dual-condition mean-reversion sniper.
    It takes the minimum of two distinct mean-reversion signals:
    1. A 5-period momentum fade that must have been persistently weak for 2 periods (ts_min).
    2. A 1-period momentum fade that is smoothed over 5 periods (decay_linear).
    Because it uses a min() function across two cross-sectional ranks, BOTH the medium-term 
    and short-term fades must be extremely oversold relative to the market to trigger a buy.
    """
    
    SIGNAL_PARAMS = frozenset({'left_delta_p', 'left_ts_p', 'right_decay_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'left_delta_p': [3, 5, 7, 10],
        'left_ts_p': [2, 3, 5],
        'right_decay_p': [3, 5, 7, 10],
        'long_thresh': [0.6, 0.7, 0.8, 0.9],   # Since min() lowers the average value, thresholds should be scaled
        'short_thresh': [0.1, 0.2, 0.3, 0.4],
        'sl_pct': [0.05, 0.08, 0.12, 0.15],    # Removing 0.03% to prevent noise overfitting
        'tp_pct': [0.10, 0.15, 0.20, 0.30],
    }

    def __init__(self, dfs, left_delta_p=5, left_ts_p=2, right_decay_p=5, long_thresh=0.8, short_thresh=0.2, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.left_delta_p = int(left_delta_p)
        self.left_ts_p = int(left_ts_p)
        self.right_decay_p = int(right_decay_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        
        # --- LEFT SIDE ---
        # rank(delta(close, 5))
        delta_5 = close_df.diff(self.left_delta_p)
        rank_delta_5 = delta_5.rank(axis=1, pct=True)
        
        # rank(-rank)
        fade_delta_5 = -1.0 * rank_delta_5
        rank_fade = fade_delta_5.rank(axis=1, pct=True)
        
        # ts_min(..., 2)
        ts_min_fade = rank_fade.rolling(self.left_ts_p).min()
        
        # rank(log(ts_min + 1e-5))
        # Adding epsilon to prevent log(0)
        log_ts_min = np.log(ts_min_fade + 1e-5)
        left_side = log_ts_min.rank(axis=1, pct=True)
        
        # --- RIGHT SIDE ---
        # -returns
        returns = close_df.pct_change(1)
        fade_returns = -1.0 * returns
        
        # rank(-returns)
        rank_fade_returns = fade_returns.rank(axis=1, pct=True)
        
        # decay_linear(..., 5)
        decayed_returns = calc_decay_linear(rank_fade_returns, self.right_decay_p)
        
        # rank(...)
        right_side = decayed_returns.rank(axis=1, pct=True)
        
        # min(left, right)
        raw_alpha = np.minimum(left_side, right_side)
        
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
