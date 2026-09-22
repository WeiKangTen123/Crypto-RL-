import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class ComplexVolumeScalar(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Complex Volume Scalar (WorldQuant Alpha #60).
    Formula: scale(rank(ts_argmax(close, p1))) - 2 * scale(rank(CLV * volume))
    
    This "HARD" factor combines the cross-sectional rank of the Accumulation/Distribution Line 
    (Close Location Value * Volume) with the rank of the time elapsed since the local high.
    It applies a mathematical `scale()` function to normalize these ranks before subtracting them,
    identifying coins that are aggressively accumulating volume near their local lows.
    """
    
    SIGNAL_PARAMS = frozenset({'p1', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'p1': [10, 15, 20, 25, 30],
        'long_thresh': [0.08, 0.09, 0.10, 0.11, 0.12],
        'short_thresh': [-0.20, -0.22, -0.25, -0.28, -0.30],
        'sl_pct': [0.01, 0.02, 0.03, 0.04, 0.05],
        'tp_pct': [0.06, 0.08, 0.10, 0.12, 0.15],
    }

    def __init__(self, dfs, p1=10, long_thresh=0.10, short_thresh=-0.15, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.p1 = int(p1)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def _scale(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scales a cross-sectional DataFrame so the absolute sum of each row is 1."""
        abs_sum = df.abs().sum(axis=1) + 1e-8
        return df.div(abs_sum, axis=0)

    def generate_signals(self) -> dict:
        open_df = pd.DataFrame({sym: df['Open'] for sym, df in self.dfs.items()})
        high_df = pd.DataFrame({sym: df['High'] for sym, df in self.dfs.items()})
        low_df = pd.DataFrame({sym: df['Low'] for sym, df in self.dfs.items()})
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        vol_df = pd.DataFrame({sym: df['Volume'] for sym, df in self.dfs.items()})
        
        # 1. ts_argmax(close, p1): index of the max close over the last p1 bars
        # np.argmax returns 0 to p1-1. We want it so that higher = more recent.
        def argmax_func(x):
            return np.argmax(x)
            
        # rolling().apply is slow, so we optimize with numpy strides or accept the hit 
        # since it's just 10,000 bars. We'll use apply with raw=True for speed.
        ts_argmax_close = close_df.rolling(self.p1).apply(argmax_func, raw=True)
        
        # rank(ts_argmax)
        rank_argmax = ts_argmax_close.rank(axis=1, pct=True)
        
        # scale(rank_argmax)
        scaled_argmax = self._scale(rank_argmax)
        
        # 2. CLV * volume
        # CLV = ((close - low) - (high - close)) / (high - low)
        clv = ((close_df - low_df) - (high_df - close_df)) / (high_df - low_df + 1e-8)
        adl = clv * vol_df
        
        # rank(CLV * volume)
        rank_adl = adl.rank(axis=1, pct=True)
        
        # scale(rank_adl)
        scaled_adl = self._scale(rank_adl)
        
        # Final Alpha = scale(rank(argmax)) - 2 * scale(rank(adl))
        raw_alpha = scaled_argmax - (2.0 * scaled_adl)
        
        # We generate signals based on the raw_alpha value (which will be between approx -2 and +1)
        for sym, df in self.dfs.items():
            alpha = raw_alpha[sym].loc[df.index]
            
            # Reverting logic vs Momentum logic is handled by Optuna thresholds (can be negative or positive)
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
