import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class ComplexVolRankMomentum(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Complex Vol-Rank VWAP Momentum (WorldQuant Alpha #47).
    Formula: ((((rank((1 / close)) * volume) / adv20) * ((high * rank((high - close))) / (sum(high, 5) / 5))) - rank((vwap - delay(vwap, 5))))
                 
    This "HARD" Alpha uses intense multi-stage cross-sectional ranking to find coins showing 
    high relative volume on price dips, combined with upper-wick momentum and VWAP acceleration.
    """
    
    SIGNAL_PARAMS = frozenset({'adv_p', 'sma_p', 'delay_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'adv_p': [10, 50, 100, 200, 300],
        'sma_p': [3, 20, 50, 100, 200],
        'delay_p': [3, 20, 50, 100, 200],
        'long_thresh': [0.4, 0.6, 0.8, 0.9, 0.95],
        'short_thresh': [0.05, 0.1, 0.3, 0.5, 0.6],
        'sl_pct': [0.01, 0.05, 0.10, 0.15, 0.20],
        'tp_pct': [0.05, 0.10, 0.20, 0.30, 0.50],
    }

    def __init__(self, dfs, adv_p=20, sma_p=5, delay_p=5, long_thresh=0.8, short_thresh=0.2, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.adv_p = int(adv_p)
        self.sma_p = int(sma_p)
        self.delay_p = int(delay_p)
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
        
        vwap_df = (high_df + low_df + close_df) / 3
        
        # rank(1 / close)
        inv_close_rank = (1.0 / close_df).rank(axis=1, pct=True)
        
        # adv
        adv = vol_df.rolling(self.adv_p).mean()
        
        # term 1 = (rank(1/close) * volume) / adv20
        # Add 1e-8 to prevent division by zero
        term1 = (inv_close_rank * vol_df) / (adv + 1e-8)
        
        # rank(high - close)
        wick_rank = (high_df - close_df).rank(axis=1, pct=True)
        
        # sum(high, 5) / 5  => SMA(high, 5)
        sma_high = high_df.rolling(self.sma_p).mean()
        
        # term 2 = (high * rank(high - close)) / sma_high
        term2 = (high_df * wick_rank) / (sma_high + 1e-8)
        
        # term 3 = rank(vwap - delay(vwap, 5))
        vwap_diff = vwap_df - vwap_df.shift(self.delay_p)
        term3 = vwap_diff.rank(axis=1, pct=True)
        
        # raw_alpha = (term1 * term2) - term3
        raw_alpha = (term1 * term2) - term3
        
        # Normalize final alpha
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
