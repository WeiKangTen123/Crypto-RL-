import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class VolumeFOMORank(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Volume-Price Correlation (FOMO/Capitulation Proxy).
    Based on the Korean Crypto Market paper's Kimchi Premium analysis.
    
    Formula: corr(delta(Volume, 1), delta(Close, 1), corr_period)
    
    High positive correlation implies Volume is surging as Price rises (FOMO regime),
    which is historically a mean-reversion short setup.
    High negative correlation implies Volume surging as Price drops (Capitulation),
    which is a mean-reversion long setup.
    
    This strategy computes the correlation for each coin, ranks them cross-sectionally,
    goes SHORT the #1 ranked (highest FOMO) and LONG the #N ranked (highest Capitulation).
    """
    
    SIGNAL_PARAMS = frozenset({'corr_period', 'delta_period'})
    
    OPTIMIZATION_RANGES = {
        'corr_period': [5, 10, 14, 21, 28],
        'delta_period': [1, 2, 3],
        'sl_pct': [0.03, 0.05, 0.07, 0.10],
        'tp_pct': [0.06, 0.10, 0.15, 0.20],
    }

    def __init__(self, dfs, corr_period=14, delta_period=1, sl_pct=0.05, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.corr_period = int(corr_period)
        self.delta_period = int(delta_period)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        corrs = {}
        
        # 1. Calculate the Volume-Price Correlation for each symbol
        for sym, df in self.dfs.items():
            vol_delta = df['Volume'].diff(self.delta_period)
            price_delta = df['Close'].diff(self.delta_period)
            
            # Compute rolling Pearson correlation
            correlation = vol_delta.rolling(window=self.corr_period, min_periods=3).corr(price_delta)
            
            # Fill NaNs with 0 to prevent ranking errors
            corrs[sym] = correlation.fillna(0)
            
        # 2. Create combined DataFrame for cross-sectional ranking
        corr_df = pd.DataFrame(corrs)
        
        # 3. Rank: ascending=False means 1 = highest positive correlation (FOMO)
        ranks = corr_df.rank(axis=1, ascending=False, method='first')
        
        n_assets = len(self.dfs)
        
        for sym in self.dfs.keys():
            self.dfs[sym]['signal'] = 0
            
            # We want to SHORT the highest FOMO (#1 ranked)
            short_cond = (ranks[sym] == 1) & (corr_df[sym] > 0.3)
            
            # We want to LONG the highest Capitulation (#N ranked)
            long_cond = (ranks[sym] == n_assets) & (corr_df[sym] < -0.3)
            
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
