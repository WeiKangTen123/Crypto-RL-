import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear, calc_ts_rank

class DoubleDecayMin(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Double Decay Chain Minimum (WorldQuant Alpha #88).
    Formula: min(rank(decay_linear(((rank(open) + rank(low)) - (rank(high) + rank(close))), 8)), 
                 ts_rank(decay_linear(correlation(ts_rank(close, 8), ts_rank(adv20, 8), 5), 3), 5))
                 
    This is an extremely HARD Alpha utilizing two separate linear-decay chains, cross-sectional ranking,
    nested time-series ranking, and rolling correlations.
    """
    
    SIGNAL_PARAMS = frozenset({'p1', 'p2', 'p3', 'p4', 'p5', 'adv_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'p1': [3, 5, 10, 20, 50],
        'p2': [3, 5, 10, 20, 50],
        'p3': [3, 10, 30, 50, 100],
        'p4': [3, 10, 30, 50, 100],
        'p5': [2, 10, 30, 50, 100],
        'adv_p': [5, 20, 50, 100, 200],
        'long_thresh': [0.4, 0.6, 0.8, 0.9, 0.95],
        'short_thresh': [0.05, 0.1, 0.3, 0.5, 0.6],
        'sl_pct': [0.01, 0.05, 0.10, 0.15, 0.20],
        'tp_pct': [0.02, 0.10, 0.20, 0.30, 0.50],
    }

    def __init__(self, dfs, p1=8, p2=8, p3=5, p4=3, p5=5, adv_p=20, long_thresh=0.8, short_thresh=0.2, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.p1 = int(p1)
        self.p2 = int(p2)
        self.p3 = int(p3)
        self.p4 = int(p4)
        self.p5 = int(p5)
        self.adv_p = int(adv_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        # Dictionaries to hold intermediate series for cross-sectional operations
        term1_dict = {}
        ts_rank_dict = {}
        
        for sym, df in self.dfs.items():
            # Term 1 logic (needs cross-sectional rank of OHLC first)
            pass
            
        # Since Alpha 88 relies on cross-sectional rank at the very root (rank(open) etc.),
        # we must combine all OHLC data first.
        open_df = pd.DataFrame({sym: df['Open'] for sym, df in self.dfs.items()})
        high_df = pd.DataFrame({sym: df['High'] for sym, df in self.dfs.items()})
        low_df = pd.DataFrame({sym: df['Low'] for sym, df in self.dfs.items()})
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        vol_df = pd.DataFrame({sym: df['Volume'] for sym, df in self.dfs.items()})
        
        # Cross-sectional ranks of OHLC
        rank_open = open_df.rank(axis=1, pct=True)
        rank_high = high_df.rank(axis=1, pct=True)
        rank_low = low_df.rank(axis=1, pct=True)
        rank_close = close_df.rank(axis=1, pct=True)
        
        # core1 = (rank(open) + rank(low)) - (rank(high) + rank(close))
        core1 = (rank_open + rank_low) - (rank_high + rank_close)
        
        # decay_linear on core1
        decay_core1 = pd.DataFrame({
            sym: calc_decay_linear(core1[sym], self.p1) for sym in core1.columns
        })
        
        # Rank 1 = cross-sectional rank of decay_core1
        rank1 = decay_core1.rank(axis=1, pct=True)
        
        # Term 2 Logic
        rank2_dict = {}
        for sym in self.dfs.keys():
            close_s = close_df[sym]
            vol_s = vol_df[sym]
            
            ts_close = calc_ts_rank(close_s, self.p2)
            adv = vol_s.rolling(self.adv_p).mean()
            ts_adv = calc_ts_rank(adv, self.p2)
            
            # correlation(ts_rank(close, p2), ts_rank(adv20, p2), p3)
            corr = ts_close.rolling(self.p3).corr(ts_adv).fillna(0)
            
            # decay_linear(corr, p4)
            decay_corr = calc_decay_linear(corr, self.p4)
            
            # ts_rank(decay, p5)
            ts_rank2 = calc_ts_rank(decay_corr, self.p5)
            rank2_dict[sym] = ts_rank2
            
        rank2 = pd.DataFrame(rank2_dict)
        
        # final alpha = min(rank1, rank2)
        # We scale it back to 0-1 percentile to make thresholding universal
        raw_alpha = pd.DataFrame(np.minimum(rank1.values, rank2.values), index=rank1.index, columns=rank1.columns)
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
