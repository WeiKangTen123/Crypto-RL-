"""
Strategy 194: Amihud ILLIQ Mean-Reversion
"""

from typing import Optional, Tuple
import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_amihud_illiq, calc_zscore, calc_atr

class AmihudIlliqMrStrategy194(BaseStrategy):
    SIGNAL_PARAMS: frozenset = frozenset({'illiq_period', 'zscore_period', 'atr_period', 'tp_mult', 'sl_mult'})

    def __init__(self, df: pd.DataFrame, 
                 illiq_period: int = 20, 
                 zscore_period: int = 200, 
                 atr_period: int = 7,
                 tp_mult: float = 1.5,
                 sl_mult: float = 1.5,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.illiq_period = illiq_period
        self.zscore_period = zscore_period
        self.atr_period = atr_period
        self.tp_mult = tp_mult
        self.sl_mult = sl_mult

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        # Indicators
        illiq = calc_amihud_illiq(df, self.illiq_period)
        df['z_illiq'] = calc_zscore(illiq, self.zscore_period)
        df['mean_20'] = df['Close'].rolling(window=20).mean()
        df['atr'] = calc_atr(df, self.atr_period)

        # Entry signals
        df['signal'] = 0
        df.loc[(df['z_illiq'] > 2.0) & (df['Close'] < df['mean_20']), 'signal'] = 1
        df.loc[(df['z_illiq'] < -2.0) & (df['Close'] > df['mean_20']), 'signal'] = -1
        
        self.df = df
        return self.df

    def manage_trade(self, row, position, entry_price, wallet=0):
        atr = row['atr']
        if position > 0:
            if row['High'] >= entry_price + self.tp_mult * atr: return 'TP', entry_price + self.tp_mult * atr
            if row['Low'] <= entry_price - self.sl_mult * atr: return 'SL', entry_price - self.sl_mult * atr
        elif position < 0:
            if row['Low'] <= entry_price - self.tp_mult * atr: return 'TP', entry_price - self.tp_mult * atr
            if row['High'] >= entry_price + self.sl_mult * atr: return 'SL', entry_price + self.sl_mult * atr
        return 'HOLD', None
