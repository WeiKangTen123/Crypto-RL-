import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_ts_rank

class TripleTsRank(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Triple TS Rank Momentum (WorldQuant Alpha #35).
    Formula: ((ts_rank(volume, 32) * (1 - ts_rank(((close + high) - low), 16))) * (1 - ts_rank(returns, 32)))
    
    This is an elegant volume-exhaustion capitulation factor.
    It multiplies three time-series ranks (values between 0.0 and 1.0) together:
    1. ts_rank(volume): Requires current volume to be extremely high relative to recent history.
    2. (1 - ts_rank(close + high - low)): Requires intraday buying pressure to be at its lowest relative to recent history.
    3. (1 - ts_rank(returns)): Requires the bar return to be at its lowest relative to recent history.
    
    When all three conditions align (Massive Volume + Historic Selling Pressure + Historic Price Drop),
    the product approaches 1.0, triggering a mean-reversion BUY signal to catch the capitulation wick.
    """
    
    SIGNAL_PARAMS = frozenset({'vol_p', 'bp_p', 'ret_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'vol_p': [15, 32, 50, 100],
        'bp_p': [10, 16, 32, 50],
        'ret_p': [15, 32, 50, 100],
        'long_thresh': [0.6, 0.7, 0.8, 0.9],
        'short_thresh': [0.05, 0.1, 0.15, 0.2],
        'sl_pct': [0.05, 0.08, 0.10, 0.15],
        'tp_pct': [0.10, 0.15, 0.20, 0.30],
    }

    def __init__(self, dfs, vol_p=32, bp_p=16, ret_p=32, long_thresh=0.8, short_thresh=0.1, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.vol_p = int(vol_p)
        self.bp_p = int(bp_p)
        self.ret_p = int(ret_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            # 1. ts_rank(volume)
            vol_rank = calc_ts_rank(df['Volume'], self.vol_p)
            
            # 2. 1 - ts_rank((close + high) - low)
            buying_pressure = (df['Close'] + df['High']) - df['Low']
            bp_rank = calc_ts_rank(buying_pressure, self.bp_p)
            bp_fade = 1.0 - bp_rank
            
            # 3. 1 - ts_rank(returns)
            returns = df['Close'].pct_change(1)
            ret_rank = calc_ts_rank(returns.fillna(0), self.ret_p)
            ret_fade = 1.0 - ret_rank
            
            # Final Alpha Product
            alpha = vol_rank * bp_fade * ret_fade
            
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
