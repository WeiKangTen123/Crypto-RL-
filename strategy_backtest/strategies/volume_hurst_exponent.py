import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_volume_hurst

class VolumeHurstExponent(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Volume Hurst exponent h(2)
    Uses a fast rolling variance ratio proxy for the Hurst Exponent on Volume.
    If H > threshold (e.g., 0.55), volume is persistent (trending).
    Coupled with a simple price momentum filter to ride the trend.
    """
    
    SIGNAL_PARAMS = frozenset({'hurst_period', 'hurst_thresh', 'sma_period'})
    
    OPTIMIZATION_RANGES = {
        'hurst_period': [60, 100, 200, 252],
        'hurst_thresh': [0.52, 0.55, 0.58, 0.60],
        'sma_period': [10, 20, 50, 100],
        'sl_pct': [0.05, 0.08, 0.12, 0.15],
        'tp_pct': [0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, hurst_period=100, hurst_thresh=0.55, sma_period=20, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.hurst_period = int(hurst_period)
        self.hurst_thresh = float(hurst_thresh)
        self.sma_period = int(sma_period)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            h_approx = calc_volume_hurst(df, period=self.hurst_period)
            sma = df['Close'].rolling(window=self.sma_period).mean()
            
            # Long when volume is persistently trending and price is in uptrend
            long_cond = (h_approx > self.hurst_thresh) & (df['Close'] > sma)
            
            # Short when volume is persistently trending and price is in downtrend
            short_cond = (h_approx > self.hurst_thresh) & (df['Close'] < sma)
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            # Cross over logic to trigger entry
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
