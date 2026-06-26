import pandas as pd
import numpy as np
import talib
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_choppiness_index, calc_keltner_channels
from typing import Tuple, Optional

class ChoppinessKeltnerBreakoutStrategy(BaseStrategy):
    """
    Choppiness Index & Keltner Channel Breakout Strategy
    Filters false breakouts that occur in choppy regimes, only taking breakouts 
    when CHOP indicates a trending regime is starting.
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.chop_period = kwargs.get('chop_period', 14)
        self.kc_period = kwargs.get('kc_period', 20)
        self.kc_mult = kwargs.get('kc_mult', 2.0)
        self.chop_threshold = kwargs.get('chop_threshold', 50.0)
        self.sl_atr_multiplier = kwargs.get('sl_atr_multiplier', 2.0)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Calc CHOP
        df['chop'] = calc_choppiness_index(df, period=self.chop_period)
        
        # 2. Calc Keltner Channels
        df['kc_upper'], df['kc_middle'], df['kc_lower'] = calc_keltner_channels(df, period=self.kc_period, mult=self.kc_mult)
        
        # Calculate ATR for stop loss
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.kc_period)
        
        # 3. CHOP conditions (CHOP < 50 AND CHOP is falling)
        chop_trending = df['chop'] < self.chop_threshold
        chop_falling = df['chop'] < df['chop'].shift(1)
        valid_regime = chop_trending & chop_falling
        
        df['signal'] = 0
        df['entry_atr'] = 0.0
        
        # Entry conditions
        long_cond = (df['Close'] > df['kc_upper']) & valid_regime
        short_cond = (df['Close'] < df['kc_lower']) & valid_regime
        
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1
        df.loc[long_cond | short_cond, 'entry_atr'] = df['atr']
        
        df['entry_atr'] = df['entry_atr'].replace(0.0, np.nan).ffill()
        
        self.df = df
        return df.astype({'signal': int})

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        entry_atr = getattr(row, 'entry_atr', 0)
        
        if pd.isna(entry_atr) or entry_atr == 0:
            entry_atr = entry_price * 0.02
            
        if position > 0:
            # Exit if it crosses back below Keltner middle
            if row['Low'] <= row['kc_middle']:
                return 'TP', row['kc_middle']
            sl_price = entry_price - (self.sl_atr_multiplier * entry_atr)
            if row['Low'] <= sl_price:
                return 'SL', sl_price
        elif position < 0:
            if row['High'] >= row['kc_middle']:
                return 'TP', row['kc_middle']
            sl_price = entry_price + (self.sl_atr_multiplier * entry_atr)
            if row['High'] >= sl_price:
                return 'SL', sl_price
                
        return 'HOLD', None
