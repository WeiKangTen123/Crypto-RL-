import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class MultiScaleMAConfluence(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Multi-Scale MA Confluence
    From: "Pairs trading with time-series deep learning models" (Scaleformer logic)
    Logic: Computes moving averages at 4 different timescales (e.g., 5, 10, 20, 60).
    A strong trend is identified when the MAs are perfectly stacked.
    Long when MA_t1 > MA_t2 > MA_t3 > MA_t4
    Short when MA_t1 < MA_t2 < MA_t3 < MA_t4
    """
    
    SIGNAL_PARAMS = frozenset({'ma1', 'ma2', 'ma3', 'ma4', 'ma_type'})
    
    OPTIMIZATION_RANGES = {
        'ma1': [3, 5, 7],
        'ma2': [10, 15, 20],
        'ma3': [25, 30, 40],
        'ma4': [50, 60, 100],
        'ma_type': ['SMA', 'EMA'],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.06, 0.10, 0.15],
    }

    def __init__(self, dfs, ma1=5, ma2=10, ma3=20, ma4=60, ma_type='SMA', sl_pct=0.05, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.ma1 = int(ma1)
        self.ma2 = int(ma2)
        self.ma3 = int(ma3)
        self.ma4 = int(ma4)
        self.ma_type = str(ma_type)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            close = df['Close']
            
            if self.ma_type == 'EMA':
                ma1_line = close.ewm(span=self.ma1, adjust=False).mean()
                ma2_line = close.ewm(span=self.ma2, adjust=False).mean()
                ma3_line = close.ewm(span=self.ma3, adjust=False).mean()
                ma4_line = close.ewm(span=self.ma4, adjust=False).mean()
            else:
                ma1_line = close.rolling(window=self.ma1).mean()
                ma2_line = close.rolling(window=self.ma2).mean()
                ma3_line = close.rolling(window=self.ma3).mean()
                ma4_line = close.rolling(window=self.ma4).mean()
            
            # Stacked moving averages for strong trend confirmation
            long_cond = (ma1_line > ma2_line) & (ma2_line > ma3_line) & (ma3_line > ma4_line)
            short_cond = (ma1_line < ma2_line) & (ma2_line < ma3_line) & (ma3_line < ma4_line)
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            # We want to trigger an entry only on the transition into a stacked state
            # so we only take the first bar it becomes true
            signal_diff = np.diff(signal, prepend=0)
            
            # 1 when transitioning into long cond, -1 when transitioning into short cond, 0 otherwise
            entry_signals = np.zeros(len(df), dtype=int)
            entry_signals[(signal == 1) & (signal_diff > 0)] = 1
            entry_signals[(signal == -1) & (signal_diff < 0)] = -1
            
            self.dfs[sym]['signal'] = entry_signals
            
        return self.dfs

    def manage_trade(self, symbol: str, bar, qty: float, entry_price: float, entry_balance: float):
        """
        Fixed RR exit management.
        """
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
