import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_vol_regime_reversal

class VolatilityRegimeReversal(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Volatility regime reversal signal (WorldQuant Alpha #1)
    Formula: rank(argmax(sign(ret<0) ? std(ret,20) : close, 5)) - 0.5
    
    Alpha score bounds between -0.5 and 0.5.
    A high alpha means the recent conditional metric reached its max recently.
    """
    
    SIGNAL_PARAMS = frozenset({'std_p', 'argmax_p', 'ts_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'std_p': [10, 20, 30],
        'argmax_p': [3, 5, 10],
        'ts_p': [5, 10, 20],
        'long_thresh': [0.1, 0.2, 0.3, 0.4],
        'short_thresh': [-0.4, -0.3, -0.2, -0.1],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.05, 0.10, 0.15],
    }

    def __init__(self, dfs, std_p=20, argmax_p=5, ts_p=10, long_thresh=0.3, short_thresh=-0.3, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.std_p = int(std_p)
        self.argmax_p = int(argmax_p)
        self.ts_p = int(ts_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            alpha = calc_vol_regime_reversal(df, std_p=self.std_p, argmax_p=self.argmax_p, ts_p=self.ts_p)
            
            # Simple breakout logic
            long_cond = alpha > self.long_thresh
            short_cond = alpha < self.short_thresh
            
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
