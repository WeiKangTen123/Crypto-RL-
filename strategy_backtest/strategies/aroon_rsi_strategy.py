import pandas as pd
import numpy as np
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class AroonRSIStrategy(BaseStrategy):
    """
    Aroon RSI Mean Reversion Strategy.
    Identifies extreme overextended conditions using Aroon Oscillator and RSI.
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.aroon_period = kwargs.get('aroon_period', 14)
        self.rsi_period = kwargs.get('rsi_period', 14)
        self.ema_period = kwargs.get('ema_period', 10)
        self.atr_period = kwargs.get('atr_period', 14)
        
        self.aroon_threshold = kwargs.get('aroon_threshold', 70)
        self.rsi_lower = kwargs.get('rsi_lower', 30)
        self.rsi_upper = kwargs.get('rsi_upper', 70)
        
        self.tp_atr_mult = kwargs.get('tp_atr_mult', 2.5)
        self.sl_atr_mult = kwargs.get('sl_atr_mult', 1.5)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Indicators
        aroon = ta.trend.AroonIndicator(high=df['High'], low=df['Low'], window=self.aroon_period)
        df['aroon_up'] = aroon.aroon_up()
        df['aroon_down'] = aroon.aroon_down()
        
        df['rsi'] = ta.momentum.RSIIndicator(close=df['Close'], window=self.rsi_period).rsi()
        df['ema_conf'] = ta.trend.EMAIndicator(close=df['Close'], window=self.ema_period).ema_indicator()
        df['atr'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=self.atr_period).average_true_range()
        
        # 2. Signal Logic
        # Long: Aroon Down > threshold AND RSI < lower
        long_cond = (df['aroon_down'] > self.aroon_threshold) & \
                    (df['rsi'] < self.rsi_lower)

        # Short: Aroon Up > threshold AND RSI > upper
        short_cond = (df['aroon_up'] > self.aroon_threshold) & \
                     (df['rsi'] > self.rsi_upper)
        
        df['signal'] = 0
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1
        
        # Forward fill ATR for SL/TP use in manage_trade if needed, 
        # but manage_trade gets the row so it's fine.
        
        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0.0,
    ) -> Tuple[str, Optional[float]]:
        
        if position == 0:
            return 'HOLD', None
            
        side = np.sign(position)
        atr = row['atr']
        
        if side == 1:
            tp_price = entry_price + (self.tp_atr_mult * atr)
            sl_price = entry_price - (self.sl_atr_mult * atr)
            if row['Low']  <= sl_price: return 'SL', sl_price

            if row['High'] >= tp_price: return 'TP', tp_price
            if row['rsi'] >= 50:
                return 'EXIT', row['Close']
        else:
            tp_price = entry_price - (self.tp_atr_mult * atr)
            sl_price = entry_price + (self.sl_atr_mult * atr)
            if row['High'] >= sl_price: return 'SL', sl_price

            if row['Low']  <= tp_price: return 'TP', tp_price
            if row['rsi'] <= 50:
                return 'EXIT', row['Close']

        return 'HOLD', None
