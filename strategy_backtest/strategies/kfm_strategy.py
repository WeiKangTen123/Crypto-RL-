import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_kalman_filter, calc_atr

class KalmanFilteredMomentumStrategy(BaseStrategy):
    """
    Kalman Filtered Momentum (KFM)
    Calculates a Kalman Filter of price to reduce noise, then uses its derivative (slope)
    to identify strong trends. Includes an ATR Chandelier Exit.
    """
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})
    
    SIGNAL_PARAMS = frozenset({
        'noise',
        'slope_lookback',
        'slope_threshold',
        'ema_trend_period',
        'atr_period',
        'chandelier_mult'
    })

    OPTIMIZATION_RANGES = {
        'noise': (0.001, 0.05),
        'slope_lookback': (1, 10),
        'slope_threshold': (0.0, 50.0),
        'ema_trend_period': (50, 300)
    }

    def __init__(self, df: pd.DataFrame, 
                 noise: float = 0.0186,
                 slope_lookback: int = 5,
                 slope_threshold: float = 33.7717,
                 ema_trend_period: int = 293,
                 atr_period: int = 6,
                 chandelier_mult: float = 3.0,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.noise = noise
        self.slope_lookback = slope_lookback
        self.slope_threshold = slope_threshold
        self.ema_trend_period = ema_trend_period
        self.atr_period = atr_period
        self.chandelier_mult = chandelier_mult

        self._s_entry_price = 0.0
        self._s_trailing_stop = 0.0
        self._s_position = 0

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        df['kalman'] = calc_kalman_filter(df['Close'], noise=self.noise)
        df['kalman_slope'] = df['kalman'].diff(self.slope_lookback)
        df['ema_trend'] = df['Close'].ewm(span=self.ema_trend_period, adjust=False).mean()
        df['atr'] = calc_atr(df, self.atr_period)
        
        regime_up = df['Close'] > df['ema_trend']
        regime_down = df['Close'] < df['ema_trend']
        
        df['signal'] = 0
        long_cond = (df['kalman_slope'] > self.slope_threshold) & regime_up
        short_cond = (df['kalman_slope'] < -self.slope_threshold) & regime_down
        
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1
        
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
                self._s_trailing_stop = entry_price - (row['atr'] * self.chandelier_mult)
            elif position < 0:
                self._s_trailing_stop = entry_price + (row['atr'] * self.chandelier_mult)

        if position > 0:
            new_stop = row['High'] - (row['atr'] * self.chandelier_mult)
            if new_stop > self._s_trailing_stop:
                self._s_trailing_stop = new_stop
                
            if row['Low'] <= self._s_trailing_stop:
                return 'EXIT', self._s_trailing_stop
                
        elif position < 0:
            new_stop = row['Low'] + (row['atr'] * self.chandelier_mult)
            if new_stop < self._s_trailing_stop:
                self._s_trailing_stop = new_stop
                
            if row['High'] >= self._s_trailing_stop:
                return 'EXIT', self._s_trailing_stop
                
        return 'HOLD', None
