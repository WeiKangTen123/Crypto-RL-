import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear

class MinDecayChains(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Min of Two Decay Chains (WorldQuant Alpha #92).
    Formula: min(
        ts_rank(decay_linear(((((high + low) / 2) + close) < (low + open)), 15), 18), 
        ts_rank(decay_linear(correlation(rank(low), rank(adv30), 7), 6), 6)
    )
    
    This "HARD" factor combines a decayed candlestick pattern (evaluating if the close is 
    lower than the open/low structure) with a decayed correlation between price and volume. 
    It applies time-series ranking to both components and takes the minimum, looking for 
    coins that exhibit BOTH structural weakness and negative price-volume correlation to trigger entries.
    """
    
    SIGNAL_PARAMS = frozenset({'cond_decay_p', 'cond_tsrank_p', 'adv_p', 'corr_p', 'corr_decay_p', 'corr_tsrank_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'cond_decay_p': [5, 15, 30, 50],
        'cond_tsrank_p': [5, 18, 30, 50],
        'adv_p': [10, 30, 50, 100],
        'corr_p': [3, 7, 14, 21],
        'corr_decay_p': [3, 6, 12, 24],
        'corr_tsrank_p': [3, 6, 12, 24],
        'long_thresh': [0.5, 0.7, 0.8, 0.9, 0.95],
        'short_thresh': [0.05, 0.1, 0.2, 0.3, 0.5],
        'sl_pct': [0.03, 0.05, 0.10, 0.15],
        'tp_pct': [0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, cond_decay_p=15, cond_tsrank_p=18, adv_p=30, corr_p=7, corr_decay_p=6, corr_tsrank_p=6, long_thresh=0.8, short_thresh=0.2, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.cond_decay_p = int(cond_decay_p)
        self.cond_tsrank_p = int(cond_tsrank_p)
        self.adv_p = int(adv_p)
        self.corr_p = int(corr_p)
        self.corr_decay_p = int(corr_decay_p)
        self.corr_tsrank_p = int(corr_tsrank_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        open_df = pd.DataFrame({sym: df['Open'] for sym, df in self.dfs.items()})
        high_df = pd.DataFrame({sym: df['High'] for sym, df in self.dfs.items()})
        low_df = pd.DataFrame({sym: df['Low'] for sym, df in self.dfs.items()})
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        vol_df = pd.DataFrame({sym: df['Volume'] for sym, df in self.dfs.items()})
        
        # --- Part 1: Candlestick logic ---
        # cond = ((((high + low) / 2) + close) < (low + open))
        cond = ((((high_df + low_df) / 2.0) + close_df) < (low_df + open_df)).astype(float)
        
        # decay_linear(cond, cond_decay_p)
        cond_decay = calc_decay_linear(cond, self.cond_decay_p)
        
        # ts_rank(cond_decay, cond_tsrank_p)
        part1 = cond_decay.rolling(self.cond_tsrank_p).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        
        # --- Part 2: Correlation logic ---
        # adv30
        adv = vol_df.rolling(self.adv_p).mean()
        
        # correlation(rank(low), rank(adv), corr_p)
        rank_low = low_df.rank(axis=1, pct=True)
        rank_adv = adv.rank(axis=1, pct=True)
        corr_val = rank_low.rolling(self.corr_p).corr(rank_adv)
        
        # decay_linear(corr, corr_decay_p)
        corr_decay = calc_decay_linear(corr_val, self.corr_decay_p)
        
        # ts_rank(corr_decay, corr_tsrank_p)
        part2 = corr_decay.rolling(self.corr_tsrank_p).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
        
        # --- Final Alpha ---
        # min(part1, part2)
        raw_alpha = pd.DataFrame(np.minimum(part1.values, part2.values), index=part1.index, columns=part1.columns)
        
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
