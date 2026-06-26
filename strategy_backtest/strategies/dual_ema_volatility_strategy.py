import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os


# Ensure BaseStrategy can be imported from the parent directory

from strategy_backtest.base_strategy import BaseStrategy

class DualEMAVolatilityStrategy(BaseStrategy):
    """
    Dual-EMA Crossover with Volatility Expansion Strategy.
    
    Logic:
      1. Crossover: EMA 9 crosses above EMA 21.
      2. Volatility Confirmation: num_trades > MA(num_trades, 50) + intensity_std * STD(num_trades, 50).
      3. Volume Check: Volume > MA(Volume, 5).
      4. Exit: EMA 9 crosses below EMA 21, price below SMA 50, or RSI exhaustion (> 85).
    """

    SIGNAL_PARAMS = frozenset([
        'ema_fast', 'ema_slow', 'sma_macro', 'intensity_period', 'intensity_std', 'rsi_period', 'rsi_threshold'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        ema_fast: int = 11,
        ema_slow: int = 25,
        sma_macro: int = 71,
        intensity_period: int = 9,
        intensity_std: float = 1.0668,
        rsi_period: int = 14,
        rsi_threshold: float = 35.6577,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.sma_macro = sma_macro
        self.intensity_period = intensity_period
        self.intensity_std = intensity_std
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        volume = df['Volume']
        num_trades = df['num_trades']

        # 1. EMAs and SMAs
        df['ema_f'] = ta.trend.ema_indicator(close, window=self.ema_fast)
        df['ema_s'] = ta.trend.ema_indicator(close, window=self.ema_slow)
        df['sma_m'] = ta.trend.sma_indicator(close, window=self.sma_macro)

        # 2. Intensity Filter
        df['intensity_ma'] = num_trades.rolling(window=self.intensity_period).mean()
        df['intensity_std_dev'] = num_trades.rolling(window=self.intensity_period).std()
        df['intensity_threshold'] = df['intensity_ma'] + self.intensity_std * df['intensity_std_dev']
        
        # Check intensity spike for current or previous 3 bars
        df['intensity_spike'] = (num_trades > df['intensity_threshold']).rolling(window=4).max() > 0

        # 3. Volume Check
        df['vol_ma5'] = volume.rolling(window=5).mean()
        df['vol_rising'] = volume > df['vol_ma5'].shift(1)

        # 4. RSI
        df['rsi'] = ta.momentum.rsi(close, window=self.rsi_period)

        # Signal Logic
        ema_cross_up = (df['ema_f'] > df['ema_s']) & (df['ema_f'].shift(1) <= df['ema_s'].shift(1))
        
        long_cond = ema_cross_up & df['intensity_spike'] & df['vol_rising']

        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1

        df['signal'] = signals
        self._prev_low_arr  = df['Low'].shift(1).values
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side    = int(np.sign(position))
        bar_idx = self._bar_index_map.get(row.name, -1)
        curr_price = float(row['Close'])
        prev_low = float(self._prev_low_arr[bar_idx]) if bar_idx > 0 and not np.isnan(self._prev_low_arr[bar_idx]) else float(row['Low'])

        if side == 1:
            # 1. Trend Reversal
            if row['ema_f'] < row['ema_s']:
                return 'EXIT', None
            
            # 2. Macro Support
            if curr_price < row['sma_m']:
                return 'EXIT', None
            
            # 3. Parabolic Exit
            if row['rsi'] > self.rsi_threshold:
                if float(row['Low']) < prev_low:
                    return 'EXIT', None

        return 'HOLD', None
