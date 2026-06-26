import pandas as pd
import numpy as np
import talib
from strategy_backtest.base_strategy import BaseStrategy

class EMARibbonRSIMomentumStrategy(BaseStrategy):
    """
    EMA Ribbon Alignment + RSI Momentum Strategy.
    Trend-following using 9, 21, 55 EMAs and RSI for confirmation.
    """
    SIGNAL_PARAMS = frozenset({'ema_fast', 'ema_med', 'ema_slow', 'rsi_period', 'rsi_threshold'})

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.ema_fast = getattr(self, 'ema_fast', 9)
        self.ema_med = getattr(self, 'ema_med', 21)
        self.ema_slow = getattr(self, 'ema_slow', 55)
        self.rsi_period = getattr(self, 'rsi_period', 14)
        self.rsi_threshold = getattr(self, 'rsi_threshold', 50)

    def generate_signals(self) -> pd.DataFrame:
        """
        Compute EMAs and RSI, then check for alignment.
        """
        self.df['ema_f'] = talib.EMA(self.df['Close'], timeperiod=self.ema_fast)
        self.df['ema_m'] = talib.EMA(self.df['Close'], timeperiod=self.ema_med)
        self.df['ema_s'] = talib.EMA(self.df['Close'], timeperiod=self.ema_slow)
        self.df['rsi'] = talib.RSI(self.df['Close'], timeperiod=self.rsi_period)

        # Long alignment: fast > med > slow AND rsi > threshold
        self.df['long_aligned'] = (self.df['ema_f'] > self.df['ema_m']) & (self.df['ema_m'] > self.df['ema_s']) & (self.df['rsi'] > self.rsi_threshold)
        # Short alignment: fast < med < slow AND rsi < threshold
        self.df['short_aligned'] = (self.df['ema_f'] < self.df['ema_m']) & (self.df['ema_m'] < self.df['ema_s']) & (self.df['rsi'] < (100 - self.rsi_threshold))

        self.df['signal'] = 0
        # Enter when alignment FIRST happens
        self.df.loc[self.df['long_aligned'] & (~self.df['long_aligned'].shift(1).fillna(False)), 'signal'] = 1
        self.df.loc[self.df['short_aligned'] & (~self.df['short_aligned'].shift(1).fillna(False)), 'signal'] = -1

        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0):
        """
        Exit when the fast EMA crosses back over the medium EMA.
        """
        if position > 0:  # Long
            if row['ema_f'] < row['ema_m']:
                return 'EXIT', None
        elif position < 0:  # Short
            if row['ema_f'] > row['ema_m']:
                return 'EXIT', None
                
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """Ensure EMA periods are ordered correctly."""
        return params.get('ema_fast', 9) < params.get('ema_med', 21) < params.get('ema_slow', 55)
