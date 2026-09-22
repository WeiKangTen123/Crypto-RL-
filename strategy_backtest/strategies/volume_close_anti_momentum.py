import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class VolumeCloseAntiMomentum(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Alpha #12
    Formula: sign(delta(vol,1)) * (-delta(close,1))
    This fades the price move when there is a volume surge.
    Goes long the top performer, and short the bottom performer.
    """
    
    SIGNAL_PARAMS = frozenset({'smoothing_period'})
    
    OPTIMIZATION_RANGES = {
        'smoothing_period': [1, 3, 5, 10],
        'sl_pct': [0.03, 0.05, 0.07],
        'tp_pct': [0.06, 0.10, 0.15],
    }

    def __init__(self, dfs, smoothing_period=3, sl_pct=0.05, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.smoothing_period = int(smoothing_period)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        alpha_scores = {}
        
        # 1. Calculate raw alpha feature for each symbol
        for sym, df in self.dfs.items():
            delta_vol = df['Volume'].diff(1)
            delta_close = df['Close'].diff(1)
            
            raw_alpha = np.sign(delta_vol) * (-delta_close)
            alpha_scores[sym] = raw_alpha
            
        # 2. Create combined DataFrame
        alpha_df = pd.DataFrame(alpha_scores)
        
        # Optional: Smooth the alpha score to reduce whipsaws
        if self.smoothing_period > 1:
            alpha_df = alpha_df.rolling(window=self.smoothing_period, min_periods=1).mean()
        
        # 3. Compute cross-sectional ranks (ascending=False so 1 is the highest alpha score)
        final_ranks = alpha_df.rank(axis=1, ascending=False, method='first')
        
        n_assets = len(self.dfs)
        
        for sym in self.dfs.keys():
            self.dfs[sym]['signal'] = 0

            # Only trade when the raw alpha value confirms direction
            # (prevents constant rotation when signal is near zero)
            long_cond = (final_ranks[sym] == 1) & (alpha_df[sym] > 0)
            short_cond = (final_ranks[sym] == n_assets) & (alpha_df[sym] < 0)
            
            signal = np.zeros(len(self.dfs[sym]), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            self.dfs[sym]['signal'] = signal
            
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
