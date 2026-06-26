import pandas as pd
import numpy as np
import talib
from strategy_backtest.base_strategy import BaseStrategy

class FisherTransformStrategy(BaseStrategy):
    """
    Fisher Transform Reversal Strategy.
    Uses the Fisher Transform to identify trend reversals and extremes.
    """
    SIGNAL_PARAMS = frozenset({'period'})

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.period = getattr(self, 'period', 10)

    def generate_signals(self) -> pd.DataFrame:
        """
        Compute Fisher Transform and generate crossover signals.
        """
        high_n = self.df['High'].rolling(window=self.period).max()
        low_n = self.df['Low'].rolling(window=self.period).min()
        
        # Value calculation with normalization to [-0.999, 0.999]
        price_range = high_n - low_n
        # Avoid division by zero
        price_range = price_range.replace(0, 0.0001)
        
        raw_value = 2 * ((self.df['Close'] - low_n) / price_range - 0.5)
        
        # EMA of raw_value
        value = np.zeros(len(self.df))
        fisher = np.zeros(len(self.df))
        
        for i in range(1, len(self.df)):
            if np.isnan(raw_value.iloc[i]):
                value[i] = 0
                fisher[i] = 0
                continue
            value[i] = 0.33 * raw_value.iloc[i] + 0.67 * value[i-1]
            v = max(min(value[i], 0.999), -0.999)
            fisher[i] = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * fisher[i-1]
            
        self.df['fisher'] = fisher
        self.df['trigger'] = self.df['fisher'].shift(1)
        
        self.df['signal'] = 0
        # Long: fisher crosses above trigger from below -threshold (or just crossover)
        # Let's use crossover as signal
        self.df.loc[(self.df['fisher'] > self.df['trigger']) & (self.df['fisher'].shift(1) <= self.df['trigger'].shift(1)), 'signal'] = 1
        # Short: fisher crosses below trigger
        self.df.loc[(self.df['fisher'] < self.df['trigger']) & (self.df['fisher'].shift(1) >= self.df['trigger'].shift(1)), 'signal'] = -1

        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0):
        """
        Exit on opposite crossover.
        """
        if position > 0:  # Long
            if row['fisher'] < row['trigger']:
                return 'EXIT', None
        elif position < 0:  # Short
            if row['fisher'] > row['trigger']:
                return 'EXIT', None
                
        return 'HOLD', None
