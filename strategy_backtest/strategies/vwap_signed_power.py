import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class VWAPSignedPower(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: SignedPower VWAP Momentum (WorldQuant Alpha #84).
    Formula: SignedPower(Ts_Rank((vwap - ts_max(vwap, 15)), 20), delta(close, 5))
    
    This "HARD" factor uses a non-linear `SignedPower` transformation. 
    It measures the time-series rank of how far VWAP is from its recent high. 
    Since VWAP in crypto varies wildly, raising it to the raw `delta(close)` power 
    would cause mathematical overflow. Instead, we adapt the exponent to use the 
    normalized percentage return, turning it into a massive non-linear amplifier.
    """
    
    SIGNAL_PARAMS = frozenset({'vwap_max_p', 'ts_rank_p', 'delta_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'vwap_max_p': [5, 15, 30, 50],
        'ts_rank_p': [5, 20, 40, 60],
        'delta_p': [2, 5, 10, 20],
        'long_thresh': [1.0, 1.2, 1.5, 2.0],
        'short_thresh': [0.1, 0.5, 0.8, 0.9],
        'sl_pct': [0.03, 0.05, 0.10, 0.15],
        'tp_pct': [0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, vwap_max_p=15, ts_rank_p=20, delta_p=5, long_thresh=1.5, short_thresh=0.5, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.vwap_max_p = int(vwap_max_p)
        self.ts_rank_p = int(ts_rank_p)
        self.delta_p = int(delta_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def _calc_vwap(self, high, low, close, volume):
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).rolling(self.vwap_max_p).sum() / (volume.rolling(self.vwap_max_p).sum() + 1e-8)
        return vwap

    def generate_signals(self) -> dict:
        high_df = pd.DataFrame({sym: df['High'] for sym, df in self.dfs.items()})
        low_df = pd.DataFrame({sym: df['Low'] for sym, df in self.dfs.items()})
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        vol_df = pd.DataFrame({sym: df['Volume'] for sym, df in self.dfs.items()})
        
        # Calculate Rolling VWAP
        vwap = self._calc_vwap(high_df, low_df, close_df, vol_df)
        
        # ts_max(vwap, vwap_max_p)
        ts_max_vwap = vwap.rolling(self.vwap_max_p).max()
        
        # vwap - ts_max
        vwap_dist = vwap - ts_max_vwap
        
        # ts_rank(vwap_dist, ts_rank_p)
        # using apply(rank) is slow, but acceptable for 10000 bars.
        def ts_rank(x):
            return pd.Series(x).rank(pct=True).iloc[-1]
            
        x_base = vwap_dist.rolling(self.ts_rank_p).apply(ts_rank, raw=False)
        
        # Prevent 0 to avoid 0 ** negative = inf
        x_base = x_base.clip(lower=1e-5)
        
        # Exponent: delta(close, delta_p) adapted to percentage return scaled by 100 for proper magnitude
        # e.g., 5% return -> exponent 5.0
        exponent = close_df.diff(self.delta_p) / (close_df.shift(self.delta_p) + 1e-8) * 100.0
        
        # SignedPower(x, a) = x^a if x > 0 else -(|x|^a)
        # Since x_base is a ts_rank > 0, we can just do x_base ** exponent
        raw_alpha = x_base ** exponent
        
        # Clean infs/nans
        raw_alpha = raw_alpha.replace([np.inf, -np.inf], np.nan).fillna(1.0)
        
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
