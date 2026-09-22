import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_roc

class RelativeMomentumRank(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Cross-Sectional Relative Momentum Ranking.
    Ranks a basket of coins by their rate of change (ROC) over `roc_period`.
    Goes long the top performer, and short the bottom performer.
    """
    
    SIGNAL_PARAMS = frozenset({'roc_period'})
    
    OPTIMIZATION_RANGES = {
        'roc_period': [14, 21, 28, 42, 60],
        'sl_pct': [0.03, 0.05, 0.07],
        'tp_pct': [0.06, 0.10, 0.15],
    }

    def __init__(self, dfs, roc_period=28, sl_pct=0.05, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.roc_period = int(roc_period)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        rocs = {}
        
        # Calculate ROC for each symbol
        for sym, df in self.dfs.items():
            df['roc'] = calc_roc(df, period=self.roc_period)
            rocs[sym] = df['roc']
            
        # Create a combined DataFrame for ranking
        roc_df = pd.DataFrame(rocs)
        
        # Rank: 1 = lowest ROC, N = highest ROC
        # But we'll rank descending, so 1 = highest ROC
        ranks = roc_df.rank(axis=1, ascending=False, method='first')
        
        # Determine number of assets
        n_assets = len(self.dfs)
        
        for sym in self.dfs.keys():
            self.dfs[sym]['signal'] = 0
            
            # Go long the #1 ranked asset if ROC > 0 (optional regime guard)
            # Go short the #N ranked asset if ROC < 0
            
            # Signal logic
            long_cond = (ranks[sym] == 1) & (roc_df[sym] > 0)
            short_cond = (ranks[sym] == n_assets) & (roc_df[sym] < 0)
            
            # Create final signal array
            signal = np.zeros(len(self.dfs[sym]), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            self.dfs[sym]['signal'] = signal
            
        return self.dfs

    def manage_trade(self, symbol: str, bar, qty: float, entry_price: float, entry_balance: float):
        """
        Fixed RR exit management for each symbol.
        """
        # We must return (action, exec_price)
        action, exec_price = 'HOLD', None
        side = 1 if qty > 0 else -1
        
        # Standard Fixed RR logic
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
