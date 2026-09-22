import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class SuperFVMAStrategy(BaseStrategy):
    """
    Super FVMA Triple Confirmation Strategy.
    Combines Supertrend for macro direction, Volume Weighted Moving Average (VWMA) as FVMA proxy, 
    and Zero Lag MACD for momentum entry timing.
    """

    OPTIMIZATION_RANGES = {
        'st_period': (5, 30),
        'st_multiplier': (1.0, 6.0),
        'fvma_period': (5, 50),
        'macd_fast': (3, 30),
        'macd_slow': (15, 100),
        'macd_signal': (3, 20),
        'sl_atr_multiplier': (0.5, 3.0),
        'entry_logic': ['TRIPLE_CONFIRM', 'MOMENTUM_ONLY', 'TREND_FOLLOWING']
    }

    SIGNAL_PARAMS = frozenset({
        'st_period', 'st_multiplier', 'fvma_period', 
        'macd_fast', 'macd_slow', 'macd_signal', 
        'sl_atr_multiplier', 'entry_logic'
    })

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.st_period = kwargs.get('st_period', 10)
        self.st_multiplier = kwargs.get('st_multiplier', 3.0)
        self.fvma_period = kwargs.get('fvma_period', 20)
        self.macd_fast = kwargs.get('macd_fast', 12)
        self.macd_slow = kwargs.get('macd_slow', 26)
        self.macd_signal = kwargs.get('macd_signal', 9)
        self.sl_atr_multiplier = kwargs.get('sl_atr_multiplier', 1.5)
        self.entry_logic = kwargs.get('entry_logic', 'TRIPLE_CONFIRM')

    def _zlema(self, series: pd.Series, period: int) -> pd.Series:
        ema1 = talib.EMA(series, timeperiod=period)
        ema2 = talib.EMA(ema1, timeperiod=period)
        return ema1 + (ema1 - ema2)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. FVMA (using VWMA as proxy)
        df['vol_price'] = df['Close'] * df['Volume']
        df['fvma'] = df['vol_price'].rolling(window=self.fvma_period).mean() / df['Volume'].rolling(window=self.fvma_period).mean()
        
        # 2. Zero Lag MACD
        df['zlema_fast'] = self._zlema(df['Close'], self.macd_fast)
        df['zlema_slow'] = self._zlema(df['Close'], self.macd_slow)
        df['zl_macd'] = df['zlema_fast'] - df['zlema_slow']
        df['zl_signal'] = self._zlema(df['zl_macd'].dropna(), self.macd_signal)
        # Re-align zl_signal due to dropna
        df['zl_signal'] = df['zl_signal'].reindex(df.index)

        # 3. Supertrend Calculation
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.st_period)
        df['atr'] = df['atr'].bfill()

        hl2 = (df['High'] + df['Low']) / 2
        df['basic_ub'] = hl2 + (self.st_multiplier * df['atr'])
        df['basic_lb'] = hl2 - (self.st_multiplier * df['atr'])

        final_ub = np.zeros(len(df))
        final_lb = np.zeros(len(df))
        supertrend = np.zeros(len(df))
        direction = np.zeros(len(df)) # 1 for Long, -1 for Short

        final_ub[0] = df['basic_ub'].iloc[0]
        final_lb[0] = df['basic_lb'].iloc[0]

        for i in range(1, len(df)):
            # Upper Band
            if (df['basic_ub'].iloc[i] < final_ub[i-1]) or (df['Close'].iloc[i-1] > final_ub[i-1]):
                final_ub[i] = df['basic_ub'].iloc[i]
            else:
                final_ub[i] = final_ub[i-1]

            # Lower Band
            if (df['basic_lb'].iloc[i] > final_lb[i-1]) or (df['Close'].iloc[i-1] < final_lb[i-1]):
                final_lb[i] = df['basic_lb'].iloc[i]
            else:
                final_lb[i] = final_lb[i-1]

            # Direction & Supertrend
            prev_direction = direction[i-1]
            if prev_direction == 1:
                if df['Close'].iloc[i] < final_lb[i]:
                    direction[i] = -1
                    supertrend[i] = final_ub[i]
                else:
                    direction[i] = 1
                    supertrend[i] = final_lb[i]
            elif prev_direction == -1:
                if df['Close'].iloc[i] > final_ub[i]:
                    direction[i] = 1
                    supertrend[i] = final_lb[i]
                else:
                    direction[i] = -1
                    supertrend[i] = final_ub[i]
            else:
                if df['Close'].iloc[i] > final_ub[i]:
                    direction[i] = 1
                    supertrend[i] = final_lb[i]
                else:
                    direction[i] = -1
                    supertrend[i] = final_ub[i]

        df['supertrend'] = supertrend
        df['st_direction'] = direction

        # 4. Entry Signals
        # Zero Lag MACD crosses above zero
        df['zl_macd_prev'] = df['zl_macd'].shift(1)
        macd_cross_zero = (df['zl_macd'] > 0) & (df['zl_macd_prev'] <= 0)
        
        above_fvma = df['Close'] > df['fvma']
        st_long = df['st_direction'] == 1

        if self.entry_logic == 'TRIPLE_CONFIRM':
            long_cond = macd_cross_zero & above_fvma & st_long
        elif self.entry_logic == 'MOMENTUM_ONLY':
            long_cond = macd_cross_zero & above_fvma
        else: # TREND_FOLLOWING
            long_cond = above_fvma & st_long
            # For trend following, we only want to enter on the FIRST bar where both are true
            long_cond = long_cond & ~(long_cond.shift(1, fill_value=False))
        
        df['signal'] = 0
        df.loc[long_cond, 'signal'] = 1

        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        # Stop loss: 1.5 * ATR below entry
        if pd.notna(row['atr']) and row['atr'] > 0:
            sl_price = entry_price - (self.sl_atr_multiplier * row['atr'])
        else:
            sl_price = entry_price * 0.98

        if position > 0:
            # Exit if Supertrend flips to red
            if row['st_direction'] == -1:
                return 'EXIT', row['Close']
                
            # Stop loss
            if row['Low'] < sl_price:
                return 'SL', sl_price

        return 'HOLD', None
