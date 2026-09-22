import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class FractalVarianceRatio(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Fractal Variance Ratio (Hurst Exponent Proxy).
    
    This strategy uses the Variance Ratio (VR) as a computationally efficient 
    proxy for the Generalized Hurst Exponent to detect fractal market regimes.
    
    VR(q) = Var(q-period returns) / (q * Var(1-period returns))
    
    - If VR(q) ~ 1.0: Market is a random walk.
    - If VR(q) > 1.0: Market is trending (Persistent, H > 0.5).
    - If VR(q) < 1.0: Market is mean-reverting (Anti-persistent, H < 0.5).
    
    This strategy calculates VR across three different time scales (q1, q2, q3) 
    over a rolling window. If ALL three scales show VR > `trend_thresh`, it 
    indicates deep multi-fractal trend alignment, triggering a breakout trade 
    in the direction of the recent momentum.
    """
    
    SIGNAL_PARAMS = frozenset({'window', 'q1', 'q2', 'q3', 'trend_thresh', 'trend_lookback'})
    
    OPTIMIZATION_RANGES = {
        'window': [50, 100, 200],
        'q1': [5, 10, 15],
        'q2': [20, 30, 40],
        'q3': [50, 60, 80],
        'trend_thresh': [1.1, 1.2, 1.3, 1.5],
        'trend_lookback': [10, 20, 50],
        'sl_pct': [0.05, 0.08, 0.12, 0.15],
        'tp_pct': [0.10, 0.20, 0.30, 0.50],
    }

    def __init__(self, dfs, window=100, q1=10, q2=30, q3=60, trend_thresh=1.2, trend_lookback=20, sl_pct=0.08, tp_pct=0.20, **kwargs):
        super().__init__(dfs, **kwargs)
        self.window = int(window)
        self.q1 = int(q1)
        self.q2 = int(q2)
        self.q3 = int(q3)
        self.trend_thresh = float(trend_thresh)
        self.trend_lookback = int(trend_lookback)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            ret_1 = df['Close'].pct_change(1)
            var_1 = ret_1.rolling(self.window).var()
            
            # VR q1
            ret_q1 = df['Close'].pct_change(self.q1)
            var_q1 = ret_q1.rolling(self.window).var()
            vr_q1 = var_q1 / (self.q1 * var_1)
            
            # VR q2
            ret_q2 = df['Close'].pct_change(self.q2)
            var_q2 = ret_q2.rolling(self.window).var()
            vr_q2 = var_q2 / (self.q2 * var_1)
            
            # VR q3
            ret_q3 = df['Close'].pct_change(self.q3)
            var_q3 = ret_q3.rolling(self.window).var()
            vr_q3 = var_q3 / (self.q3 * var_1)
            
            # Trend Direction
            momentum = df['Close'].pct_change(self.trend_lookback)
            
            # Fractal Trend Alignment
            fractal_trending = (vr_q1 > self.trend_thresh) & (vr_q2 > self.trend_thresh) & (vr_q3 > self.trend_thresh)
            
            long_cond = fractal_trending & (momentum > 0)
            short_cond = fractal_trending & (momentum < 0)
            
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
