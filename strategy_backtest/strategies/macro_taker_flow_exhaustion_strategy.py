import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os


# Ensure BaseStrategy can be imported from the parent directory

from strategy_backtest.base_strategy import BaseStrategy

class MacroTakerFlowExhaustionStrategy(BaseStrategy):
    """
    Macro Taker-Flow Exhaustion Strategy
    
    Logic:
      1. Timeframe: 4H preferred.
      2. Trend Extreme: Price is at a N-period High (for Short) or Low (for Long).
      3. Taker Exhaustion: 
         - Short: taker_buy_ratio > high_threshold (e.g., 0.65) - Buying Exhaustion.
         - Long: taker_buy_ratio < low_threshold (e.g., 0.35) - Selling Climax.
      4. Exit: Price touches M-period EMA (Mean Reversion) or hit SL.
    """

    SIGNAL_PARAMS = frozenset([
        'lookback', 'ema_period', 'taker_high_threshold', 'taker_low_threshold'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        lookback: int = 46,
        ema_period: int = 129,
        taker_high_threshold: float = 0.6982,
        taker_low_threshold: float = 0.423,
        sl_pct: float = 0.0127, # Default SL if climax candle logic is too complex for row-by-row
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.lookback = lookback
        self.ema_period = ema_period
        self.taker_high_threshold = taker_high_threshold
        self.taker_low_threshold = taker_low_threshold
        self.sl_pct = sl_pct

        # Per-side state for trade management
        self._s = {
            1:  dict(entry_price=0.0, sl_price=0.0),
            -1: dict(entry_price=0.0, sl_price=0.0),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        taker_vol = df['taker_buy_base_vol']

        # 1. Donchian Channels (High/Low lookback)
        # Shifted by 1 to avoid using current bar for high/low comparison
        df['dc_high'] = high.rolling(window=self.lookback).max().shift(1)
        df['dc_low'] = low.rolling(window=self.lookback).min().shift(1)

        # 2. Taker Ratio
        df['taker_ratio'] = taker_vol / (volume + 1e-10)

        # 3. EMA for Mean Reversion Target
        df['target_ema'] = ta.trend.ema_indicator(close, window=self.ema_period)

        # Signals
        # Short: Price at/above DC High AND Taker Ratio > Threshold
        short_cond = (close >= df['dc_high']) & (df['taker_ratio'] > self.taker_high_threshold)
        
        # Long: Price at/below DC Low AND Taker Ratio < Threshold
        long_cond = (close <= df['dc_low']) & (df['taker_ratio'] < self.taker_low_threshold)

        # Edge detection: fire only on the first bar conditions become true
        long_edge  = long_cond  & ~long_cond.shift(1, fill_value=False)
        short_edge = short_cond & ~short_cond.shift(1, fill_value=False)

        signals = np.zeros(len(df), dtype=int)
        signals[long_edge.values]  = 1
        signals[short_edge.values] = -1

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
            # SL: Break of the "climax" candle's extreme
            # Since 'row' is the bar AFTER the signal candle in engine.py loop
            # we'll approximate with a fixed % or previous bar extreme if we had it.
            # For simplicity in this engine, we use fixed % SL.
            s['sl_price'] = entry_price * (1.0 - side * self.sl_pct)

        curr_close = float(row['Close'])
        target_ema = float(row['target_ema'])

        if side == 1:
            if float(row['Low'])  <= s['sl_price']: return 'SL', s['sl_price']
            if float(row['High']) >= target_ema and curr_close > entry_price: return 'TP', target_ema
        else:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']
            if float(row['Low'])  <= target_ema and curr_close < entry_price: return 'TP', target_ema

        return 'HOLD', None
