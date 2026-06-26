import pandas as pd
import numpy as np
import ta
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy

class RSITrendFilterStrategy(BaseStrategy):
    """
    RSI Trend Filter Strategy
    Buys oversold RSI dips during an established uptrend (price > 200 EMA).
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        self.ema_period = kwargs.get('ema_period', 200)
        self.rsi_period = kwargs.get('rsi_period', 14)
        self.rsi_oversold = kwargs.get('rsi_oversold', 35)
        self.rsi_overbought = kwargs.get('rsi_overbought', 65)
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.05)
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.02)
        super().__init__(df, **kwargs)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        df['EMA'] = ta.trend.ema_indicator(df['Close'], window=self.ema_period)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=self.rsi_period)
        
        df['signal'] = 0
        
        # Long entry: price > EMA and RSI crosses above oversold
        rsi_cross_above = (df['RSI'] > self.rsi_oversold) & (df['RSI'].shift(1) <= self.rsi_oversold)
        long_cond = (df['Close'] > df['EMA']) & rsi_cross_above
        
        # Short entry: price < EMA and RSI crosses below overbought
        rsi_cross_below = (df['RSI'] < self.rsi_overbought) & (df['RSI'].shift(1) >= self.rsi_overbought)
        short_cond = (df['Close'] < df['EMA']) & rsi_cross_below
        
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1
        
        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        if position > 0:
            sl_price = entry_price * (1 - self.stop_loss_pct)
            tp_price = entry_price * (1 + self.take_profit_pct)
            if row['Low']  <= sl_price: return 'SL', sl_price

            if row['High'] >= tp_price: return 'TP', tp_price
            if row['Close'] < row['EMA']:
                return 'EXIT', row['Close']

        elif position < 0:
            sl_price = entry_price * (1 + self.stop_loss_pct)
            tp_price = entry_price * (1 - self.take_profit_pct)
            if row['High'] >= sl_price: return 'SL', sl_price

            if row['Low']  <= tp_price: return 'TP', tp_price
            if row['Close'] > row['EMA']:
                return 'EXIT', row['Close']
                
        return 'HOLD', None
