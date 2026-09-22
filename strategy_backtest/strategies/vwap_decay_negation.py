import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear

class VwapDecayNegation(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: VWAP Decay Negation (WorldQuant Alpha #57).
    Formula: -(1 * ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2)))
                 
    This "HARD" Alpha measures mean-reversion to the VWAP, but scales the reversion 
    strength inversely by the decayed cross-sectional rank of how recently each coin 
    hit its 30-day maximum price. 
    """
    
    SIGNAL_PARAMS = frozenset({'p1', 'p2', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'p1': [30, 60, 100, 200, 300],          # ts_argmax window
        'p2': [2, 10, 30, 50, 100],             # decay_linear window
        'long_thresh': [0.4, 0.6, 0.8, 0.9, 0.95],
        'short_thresh': [0.05, 0.1, 0.3, 0.5, 0.6],
        'sl_pct': [0.01, 0.05, 0.10, 0.15, 0.20],
        'tp_pct': [0.05, 0.10, 0.20, 0.30, 0.50],
    }

    def __init__(self, dfs, p1=30, p2=2, long_thresh=0.8, short_thresh=0.2, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.p1 = int(p1)
        self.p2 = int(p2)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        # We need a cross-sectional DataFrame for ts_argmax
        open_df = pd.DataFrame({sym: df['Open'] for sym, df in self.dfs.items()})
        high_df = pd.DataFrame({sym: df['High'] for sym, df in self.dfs.items()})
        low_df = pd.DataFrame({sym: df['Low'] for sym, df in self.dfs.items()})
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        
        # Approximate VWAP using Typical Price
        vwap_df = (high_df + low_df + close_df) / 3
        
        # ts_argmax: Index of the maximum value within the rolling window p1
        # In pandas, rolling().apply(np.argmax) returns the 0-based index from the start of the window.
        # We want the "time since max", which is p1 - 1 - argmax, or just the argmax itself if we treat it uniformly.
        # Let's just use rolling.apply(np.argmax).
        ts_argmax_df = close_df.rolling(self.p1).apply(lambda x: np.argmax(x), raw=True)
        
        # Cross-sectional rank of ts_argmax
        rank_argmax = ts_argmax_df.rank(axis=1, pct=True)
        
        # decay_linear on the rank
        decay_rank = pd.DataFrame({
            sym: calc_decay_linear(rank_argmax[sym], self.p2) for sym in rank_argmax.columns
        })
        
        # Protect against division by zero
        decay_rank = decay_rank.replace(0, np.nan)
        
        # Alpha: -(close - vwap) / decay_rank
        raw_alpha = -(close_df - vwap_df) / decay_rank
        
        # Cross-sectional rank the final alpha to normalize it to 0-1
        final_alpha_rank = raw_alpha.rank(axis=1, pct=True)
        
        for sym, df in self.dfs.items():
            alpha = final_alpha_rank[sym].loc[df.index]
            
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
