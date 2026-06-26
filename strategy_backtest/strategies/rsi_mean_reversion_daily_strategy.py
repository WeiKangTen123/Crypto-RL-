import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class RSIMeanReversionDailyStrategy(BaseStrategy):
    """
    RSI Mean Reversion (Daily) Strategy
    
    Logic:
      1. Entry Long: RSI(5) < 30.
      2. Entry Short: RSI(5) > 70.
      3. Exit: RSI(5) crosses opposite threshold or time-based (5 bars).
    """

    SIGNAL_PARAMS = frozenset([
        'rsi_period', 'rsi_low', 'rsi_high', 'max_hold_bars'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        rsi_period: int = 11,
        rsi_low: float = 30.0,
        rsi_high: float = 70.0,
        max_hold_bars: int = 5,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.rsi_period = rsi_period
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.max_hold_bars = max_hold_bars

        # Per-side state for trade management
        self._s = {
            1:  dict(entry_price=0.0, bar_count=0),
            -1: dict(entry_price=0.0, bar_count=0),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']

        # 1. RSI(5)
        df['rsi'] = ta.momentum.rsi(close, window=self.rsi_period)

        # 2. SMA(200) Trend Filter
        df['sma_200'] = ta.trend.sma_indicator(close, window=200)

        # Signals
        # Long only if above SMA 200 (bullish trend)
        long_cond = (df['rsi'] < self.rsi_low) & (close > df['sma_200'])
        # Short only if below SMA 200 (bearish trend)
        short_cond = (df['rsi'] > self.rsi_high) & (close < df['sma_200'])

        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1
        signals[short_cond] = -1

        df['signal'] = signals
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s = self._s[side]

        # Initialize trade state if new
        if entry_price != s['entry_price']:
            s['entry_price'] = entry_price
            s['bar_count'] = 0

        s['bar_count'] += 1
        rsi = float(row['rsi'])

        # 1. Take Profit / Exit on RSI Reversal
        if side == 1 and rsi > self.rsi_high:
            return 'EXIT', None
        if side == -1 and rsi < self.rsi_low:
            return 'EXIT', None

        # 2. Time-based Exit
        if s['bar_count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
