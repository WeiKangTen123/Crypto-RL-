import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_supertrend, calc_choppiness_index, calc_adx, calc_atr

class ChoppinessGatedSupertrendStrategy(BaseStrategy):
    """
    Choppiness-Gated Supertrend (CGS)
    Uses Supertrend for trend-following, but explicitly blocks entries during
    ranging markets using the Choppiness Index and ADX as regime guards.
    """
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})
    
    SIGNAL_PARAMS = frozenset({
        'st_period',
        'st_multiplier',
        'chop_period',
        'chop_threshold',
        'adx_period',
        'adx_threshold',
        'atr_period',
        'sl_atr_mult'
    })

    OPTIMIZATION_RANGES = {
        'st_period': (7, 21),
        'st_multiplier': (1.5, 4.5),
        'chop_threshold': (30.0, 45.0),
        'adx_threshold': (20.0, 35.0)
    }

    def __init__(self, df: pd.DataFrame, 
                 st_period: int = 15,
                 st_multiplier: float = 3.842,
                 chop_period: int = 14,
                 chop_threshold: float = 41.8809,
                 adx_period: int = 14,
                 adx_threshold: float = 21.5031,
                 atr_period: int = 27,
                 sl_atr_mult: float = 2.3014,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.st_period = st_period
        self.st_multiplier = st_multiplier
        self.chop_period = chop_period
        self.chop_threshold = chop_threshold
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult

        self._s_entry_price = 0.0
        self._s_position = 0
        self._s_stop_loss = 0.0

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        df['st_val'], df['st_dir'] = calc_supertrend(df, period=self.st_period, multiplier=self.st_multiplier)
        df['chop'] = calc_choppiness_index(df, period=self.chop_period)
        df['adx'] = calc_adx(df, period=self.adx_period)
        df['atr'] = calc_atr(df, period=self.atr_period)
        
        st_flip_up = (df['st_dir'] == 1) & (df['st_dir'].shift(1) == -1)
        st_flip_down = (df['st_dir'] == -1) & (df['st_dir'].shift(1) == 1)
        
        trending_regime = (df['chop'] < self.chop_threshold) & (df['adx'] > self.adx_threshold)
        
        df['signal'] = 0
        df.loc[st_flip_up & trending_regime, 'signal'] = 1
        df.loc[st_flip_down & trending_regime, 'signal'] = -1
        
        self.df = df
        return self.df

    def manage_trade(
        self,
        row: pd.Series,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        if position != self._s_position or entry_price != self._s_entry_price:
            self._s_position = position
            self._s_entry_price = entry_price
            
            if position > 0:
                self._s_stop_loss = entry_price - (row['atr'] * self.sl_atr_mult)
            elif position < 0:
                self._s_stop_loss = entry_price + (row['atr'] * self.sl_atr_mult)

        if position > 0:
            if row['st_dir'] == -1:
                return 'EXIT', None
            if row['Low'] <= self._s_stop_loss:
                return 'SL', self._s_stop_loss
                
        elif position < 0:
            if row['st_dir'] == 1:
                return 'EXIT', None
            if row['High'] >= self._s_stop_loss:
                return 'SL', self._s_stop_loss

        return 'HOLD', None
