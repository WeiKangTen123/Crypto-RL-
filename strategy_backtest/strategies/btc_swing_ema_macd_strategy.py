import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os


# Ensure BaseStrategy can be imported from the parent directory

from strategy_backtest.base_strategy import BaseStrategy

class BTCSwingEMAMACD(BaseStrategy):
    """
    BTC Swing Trading Strategy (from StratBase.ai metadata)
    
    Logic:
      - Timeframe: 4H preferred.
      - Trend Filter: Price must be above EMA 20.
      - Momentum: RSI (14) must be above 50.
      - Confirmation: MACD Line crosses above Signal Line (Golden Cross).
      - Exit: Fixed 8% Take Profit and 3% Stop Loss.
    """

    SIGNAL_PARAMS = frozenset([
        'ema_window', 'rsi_window', 'rsi_threshold',
        'macd_fast', 'macd_slow', 'macd_signal'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        ema_window: int = 20,
        rsi_window: int = 14,
        rsi_threshold: float = 50.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        tp_pct: float = 0.08,  # 8%
        sl_pct: float = 0.03,  # 3%
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.ema_window = ema_window
        self.rsi_window = rsi_window
        self.rsi_threshold = rsi_threshold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']

        # 1. EMA Trend Filter
        df['ema_filter'] = ta.trend.ema_indicator(close, window=self.ema_window)

        # 2. RSI Momentum
        df['rsi'] = ta.momentum.rsi(close, window=self.rsi_window)

        # 3. MACD Golden Cross
        macd_obj = ta.trend.MACD(
            close, 
            window_fast=self.macd_fast, 
            window_slow=self.macd_slow, 
            window_sign=self.macd_signal
        )
        df['macd'] = macd_obj.macd()
        df['macd_signal'] = macd_obj.macd_signal()

        # Signal Logic: Price > EMA AND RSI > 50 AND MACD Cross Up
        macd_cross_up = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        
        long_cond = (close > df['ema_filter']) & (df['rsi'] > self.rsi_threshold) & macd_cross_up

        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1
        
        # StratBase usually focuses on Long for this swing strat
        df['signal'] = signals
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        
        # Fixed TP/SL relative to entry price (Intrabar check)
        if side == 1:
            sl_price = entry_price * (1 - self.sl_pct)
            tp_price = entry_price * (1 + self.tp_pct)
            if float(row['Low'])  <= sl_price: return 'SL', sl_price

            if float(row['High']) >= tp_price: return 'TP', tp_price

        elif side == -1:
            sl_price = entry_price * (1 + self.sl_pct)
            tp_price = entry_price * (1 - self.tp_pct)
            if float(row['High']) >= sl_price: return 'SL', sl_price

            if float(row['Low'])  <= tp_price: return 'TP', tp_price

        return 'HOLD', None
