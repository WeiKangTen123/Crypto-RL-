import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_vwap

class VwapDistanceRatio(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: WorldQuant Alpha #42.
    Formula: rank(vwap - close) / rank(vwap + close)
    This computes a cross-sectional score at each timestep.
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
        vwap_pct_dev = {}

        # 1. Calculate VWAP % deviation for each symbol (scale-invariant)
        for sym, df in self.dfs.items():
            vwap = calc_vwap(df)
            # Normalise by close so BTC/XRP are on the same scale
            vwap_pct_dev[sym] = (vwap - df['Close']) / (df['Close'] + 1e-10)

        # 2. Create combined DataFrame for cross-sectional ranking
        vmc_df = pd.DataFrame(vwap_pct_dev)

        # 3. Compute Alpha #42 score as rank of normalised VWAP deviation
        alpha_42 = vmc_df.rank(axis=1, method='first')
        
        # Optional: Smooth the alpha score to reduce whipsaws
        if self.smoothing_period > 1:
            alpha_42 = alpha_42.rolling(window=self.smoothing_period, min_periods=1).mean()
        
        # 5. Rank the final alpha score to select long/shorts
        # ascending=False so 1 is the highest alpha score (LONG)
        final_ranks = alpha_42.rank(axis=1, ascending=False, method='first')
        
        n_assets = len(self.dfs)
        
        for sym in self.dfs.keys():
            self.dfs[sym]['signal'] = 0
            
            # Go long the #1 ranked asset
            long_cond = (final_ranks[sym] == 1)
            # Go short the #N ranked asset
            short_cond = (final_ranks[sym] == n_assets)
            
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
