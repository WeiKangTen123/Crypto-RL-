import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_vwap

class CorrelationMatrixGate(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Correlation Matrix Gate (WorldQuant Alpha #74).
    Formula: ((rank(correlation(close, sum(adv30, 37), 15)) < rank(correlation(rank(((high * 0.026) + (vwap * (1 - 0.026)))), rank(volume), 11))) * -1)
    
    This is an exceptionally "HARD" boolean gate alpha. It evaluates two entirely distinct 
    moving correlation structures and fires a signal when their cross-sectional ranks cross.
    
    1. LEFT CORRELATION: Measures the 15-period correlation between the Close price and the 
       sum of the 30-period average volume over the last 37 periods. (Are prices tracking heavy historical volume?).
    2. RIGHT CORRELATION: Measures the 11-period correlation between the cross-sectional rank 
       of a High/VWAP price blend and the rank of Volume. (Are the most heavily bought coins 
       the ones with the most volume?).
    3. THE GATE: If the Left Correlation rank falls BELOW the Right Correlation rank, it fires 
       a short (-1) signal. If it rises ABOVE, it fires a long (1) signal.
       
    This exploits massive liquidity flow differentials by pitting long-term volume correlation 
    against short-term cross-sectional volume ranking.
    """
    
    SIGNAL_PARAMS = frozenset({'adv_p', 'sum_p', 'corr_left_p', 'corr_right_p', 'blend_ratio'})
    
    OPTIMIZATION_RANGES = {
        'adv_p': [15, 30, 45],
        'sum_p': [20, 37, 50],
        'corr_left_p': [10, 15, 20],
        'corr_right_p': [7, 11, 15],
        'blend_ratio': [0.01, 0.026, 0.05, 0.10],
        'sl_pct': [0.05, 0.08, 0.10, 0.15],
        'tp_pct': [0.10, 0.15, 0.20, 0.30],
    }

    def __init__(self, dfs, adv_p=30, sum_p=37, corr_left_p=15, corr_right_p=11, blend_ratio=0.026, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.adv_p = int(adv_p)
        self.sum_p = int(sum_p)
        self.corr_left_p = int(corr_left_p)
        self.corr_right_p = int(corr_right_p)
        self.blend_ratio = float(blend_ratio)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        high_df = pd.DataFrame({sym: df['High'] for sym, df in self.dfs.items()})
        vol_df = pd.DataFrame({sym: df['Volume'] for sym, df in self.dfs.items()})
        
        # Calculate VWAP manually for all coins
        vwap_df = pd.DataFrame()
        for sym, df in self.dfs.items():
            vwap_df[sym] = calc_vwap(df)
            
        # --- LEFT SIDE ---
        # adv30
        adv30 = vol_df.rolling(self.adv_p).mean()
        # sum(adv30, 37)
        sum_adv = adv30.rolling(self.sum_p).sum()
        # correlation(close, sum_adv, 15)
        corr_left = close_df.rolling(self.corr_left_p).corr(sum_adv)
        # rank(corr_left)
        left_rank = corr_left.rank(axis=1, pct=True)
        
        # --- RIGHT SIDE ---
        # blend = (high * 0.026) + (vwap * (1 - 0.026))
        blend = (high_df * self.blend_ratio) + (vwap_df * (1.0 - self.blend_ratio))
        # rank(blend)
        rank_blend = blend.rank(axis=1, pct=True)
        # rank(volume)
        rank_vol = vol_df.rank(axis=1, pct=True)
        # correlation(rank(blend), rank(volume), 11)
        corr_right = rank_blend.rolling(self.corr_right_p).corr(rank_vol)
        # rank(corr_right)
        right_rank = corr_right.rank(axis=1, pct=True)
        
        # --- THE GATE ---
        # If left < right, short (-1). If left > right, long (1).
        
        for sym, df in self.dfs.items():
            sym_left = left_rank[sym].loc[df.index]
            sym_right = right_rank[sym].loc[df.index]
            
            long_cond = sym_left > sym_right
            short_cond = sym_left < sym_right
            
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
