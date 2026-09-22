import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_cvd_absorption_divergence

class CVDAbsorptionDivergence(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: CVD Absorption Divergence.
    """
    SIGNAL_PARAMS = frozenset({'window', 'threshold', 'sl_pct', 'tp_pct'})
    
    OPTIMIZATION_RANGES = {
        'window': [10, 20, 30],
        'threshold': [0.3, 0.5, 0.7],
        'sl_pct': [0.03, 0.05, 0.10],
        'tp_pct': [0.05, 0.10, 0.20],
    }

    def __init__(self, dfs, window=20, threshold=0.5, sl_pct=0.04, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.window = int(window)
        self.threshold = float(threshold)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            sig_raw = calc_cvd_absorption_divergence(df, self.window)
            
            long_cond = sig_raw > self.threshold
            short_cond = sig_raw < -self.threshold
            
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
