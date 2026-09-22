import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear

class DecayLinearMomentum(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Delta Decay Fade x Momentum (WorldQuant Alpha #39).
    Formula: ((-1 * rank((delta(close, 7) * (1 - rank(decay_linear((volume / adv20), 9)))))) * (1 + rank(sum(returns, 250))))
    
    This is a HARD difficulty Alpha requiring both the custom `decay_linear` moving average
    and multi-stage Cross-Sectional Ranking across the entire portfolio.
    """
    
    SIGNAL_PARAMS = frozenset({'delta_p', 'decay_p', 'adv_p', 'ret_sum_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'delta_p': [2, 7, 14, 30, 50],
        'decay_p': [3, 9, 20, 50, 100],
        'adv_p': [5, 20, 50, 100, 200],
        'ret_sum_p': [10, 50, 100, 250, 500],
        'long_thresh': [0.5, 0.7, 0.9, 0.95],
        'short_thresh': [0.05, 0.1, 0.3, 0.5],
        'sl_pct': [0.01, 0.05, 0.10, 0.15, 0.20],
        'tp_pct': [0.02, 0.10, 0.20, 0.30, 0.50],
    }

    def __init__(self, dfs, delta_p=7, decay_p=9, adv_p=20, ret_sum_p=250, long_thresh=0.8, short_thresh=0.2, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.delta_p = int(delta_p)
        self.decay_p = int(decay_p)
        self.adv_p = int(adv_p)
        self.ret_sum_p = int(ret_sum_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        # Step 1: Precompute the individual series for each coin
        decay_vol_dict = {}
        close_delta_dict = {}
        sum_ret_dict = {}
        
        for sym, df in self.dfs.items():
            adv = df['Volume'].rolling(self.adv_p).mean()
            vol_ratio = df['Volume'] / (adv + 1e-9)
            decay_vol_dict[sym] = calc_decay_linear(vol_ratio, self.decay_p)
            
            close_delta_dict[sym] = df['Close'].diff(self.delta_p)
            
            returns = df['Close'].pct_change()
            sum_ret_dict[sym] = returns.rolling(self.ret_sum_p).sum()

        # Combine into cross-sectional DataFrames
        df_decay_vol = pd.DataFrame(decay_vol_dict)
        df_close_delta = pd.DataFrame(close_delta_dict)
        df_sum_ret = pd.DataFrame(sum_ret_dict)
        
        # Step 2: Cross-Sectional Ranking Phase
        # Rank 1: rank(decay_linear((volume / adv20), 9))
        rank1 = df_decay_vol.rank(axis=1, pct=True)
        
        # Term 1: delta(close, 7) * (1 - rank1)
        term1 = df_close_delta * (1 - rank1)
        
        # Rank 2: rank(term1)
        rank2 = term1.rank(axis=1, pct=True)
        
        # Rank 3: rank(sum(returns, 250))
        rank3 = df_sum_ret.rank(axis=1, pct=True)
        
        # Final Alpha: -1 * rank2 * (1 + rank3)
        # We can then scale this final alpha to a 0-1 percentile rank for easy thresholding
        raw_alpha = -1 * rank2 * (1 + rank3)
        final_alpha_rank = raw_alpha.rank(axis=1, pct=True)
        
        # Step 3: Distribute signals back to original DataFrames
        for sym, df in self.dfs.items():
            # Align alpha back to df's exact index to handle missing bars (like MATIC)
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
