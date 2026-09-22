import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_csi

class CandleSentimentIndex(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Candle Sentiment Index (CSI)
    CSI = (POS_days - NEG_days) / N
    Ranges from -1 to 1.
    If CSI is high, the asset is printing mostly green candles (bullish trend).
    If CSI is low, the asset is printing mostly red candles (bearish trend).
    We take a momentum/trend-following approach.
    """
    
    SIGNAL_PARAMS = frozenset({'csi_period', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'csi_period': [10, 20, 30, 60],
        'long_thresh': [0.2, 0.3, 0.4, 0.5],
        'short_thresh': [-0.5, -0.4, -0.3, -0.2],
        'sl_pct': [0.05, 0.08, 0.12],
        'tp_pct': [0.05, 0.10, 0.20],
    }

    def __init__(self, dfs, csi_period=20, long_thresh=0.3, short_thresh=-0.3, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.csi_period = int(csi_period)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            csi = calc_csi(df, period=self.csi_period)
            
            long_cond = csi > self.long_thresh
            short_cond = csi < self.short_thresh
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            # Extract only the moment of crossover to avoid spamming orders
            signal_diff = np.diff(signal, prepend=0)
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
