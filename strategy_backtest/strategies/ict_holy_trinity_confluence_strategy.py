import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from functools import reduce

from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import detect_fvg, detect_swing_high_low, calc_supertrend, calc_macd, calc_rsi

class ICTHolyTrinityConfluenceStrategy(BaseStrategy):
    """
    ICT Holy Trinity Confluence Strategy

    This strategy aims to identify high-probability trading setups by
    confluence of Liquidity Sweeps, Market Structure Shifts (MSS), and Fair Value Gaps (FVG).
    Filters include Supertrend, MACD, and RSI.
    """

    OPTIMIZATION_RANGES = {
        "swing_lookback": (20, 50),
        "confluence_window": (1, 10),
        "st_period": (10, 20),
        "st_multiplier": (2.0, 4.0),
        "macd_fast": (8, 16),
        "macd_slow": (21, 31),
        "macd_signal": (7, 11),
        "rsi_period": (10, 20),
        "rsi_long_max": (60, 80),
        "rsi_short_min": (20, 40),
    }

    def __init__(self, 
                 df: pd.DataFrame,
                 swing_lookback: int = 31, 
                 confluence_window: int = 5,
                 st_period: int = 11,
                 st_multiplier: float = 3.9952,
                 macd_fast: int = 13,
                 macd_slow: int = 30,
                 macd_signal: int = 13,
                 rsi_period: int = 19,
                 rsi_long_max: float = 70,
                 rsi_short_min: float = 30,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.swing_lookback = swing_lookback
        self.confluence_window = confluence_window
        self.st_period = st_period
        self.st_multiplier = st_multiplier
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.rsi_long_max = rsi_long_max
        self.rsi_short_min = rsi_short_min

    def generate_signals(self) -> pd.DataFrame:
        """
        Generates trading signals based on Holy Trinity (Sweep + MSS + FVG) + Filters.
        """
        df = self.df
        if len(df) < self.swing_lookback * 2 + 50:
            df['signal'] = 0
            return df

        # 1. Detect Swing Highs and Lows
        is_swing_high, is_swing_low = detect_swing_high_low(df, lookback=self.swing_lookback)
        
        # is_swing_high/low[i] is True at the CONFIRMATION bar (lookback bars after the pivot).
        # Use shift(swing_lookback) to retrieve the pivot bar's actual High/Low value,
        # then ffill so the value propagates from confirmation time onward (no look-ahead).
        swing_low_vals  = df['Low'].shift(self.swing_lookback).where(is_swing_low).ffill()
        swing_high_vals = df['High'].shift(self.swing_lookback).where(is_swing_high).ffill()

        # Liquidity Sweep:
        # Bullish Sweep: Price goes below recent swing low
        bullish_sweep = df['Low'] < swing_low_vals.shift(1)
        # Bearish Sweep: Price goes above recent swing high
        bearish_sweep = df['High'] > swing_high_vals.shift(1)

        # 2. Market Structure Shift (MSS)
        # Simplified MSS: Close > previous High (bullish) after a sweep
        bullish_mss = df['Close'] > df['High'].shift(1)
        bearish_mss = df['Close'] < df['Low'].shift(1)

        # 3. Detect Fair Value Gaps
        bullish_fvg, bearish_fvg = detect_fvg(df)

        # 4. Filters
        _, st_direction = calc_supertrend(df, period=self.st_period, multiplier=self.st_multiplier)
        macd_line, macd_signal_line, _ = calc_macd(df, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
        rsi = calc_rsi(df['Close'], period=self.rsi_period)

        # Long Filter: ST Green, MACD Line > Signal, RSI < 70
        long_filter = (st_direction == 1) & (macd_line > macd_signal_line) & (rsi < self.rsi_long_max)
        # Short Filter: ST Red, MACD Line < Signal, RSI > 30
        short_filter = (st_direction == -1) & (macd_line < macd_signal_line) & (rsi > self.rsi_short_min)

        # --- Confluence Logic ---
        # Look for the triad within a small window
        recent_bullish_sweep = bullish_sweep.rolling(window=self.confluence_window).max() > 0
        recent_bullish_mss = bullish_mss.rolling(window=self.confluence_window).max() > 0
        
        recent_bearish_sweep = bearish_sweep.rolling(window=self.confluence_window).max() > 0
        recent_bearish_mss = bearish_mss.rolling(window=self.confluence_window).max() > 0

        # Initialize signals
        signals = pd.Series(0, index=df.index)

        # Buy signal
        buy_condition = (bullish_fvg) & recent_bullish_sweep & recent_bullish_mss & long_filter
        signals[buy_condition] = 1

        # Sell signal
        sell_condition = (bearish_fvg) & recent_bearish_sweep & recent_bearish_mss & short_filter
        signals[sell_condition] = -1
        
        df['signal'] = signals
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        """
        Simple manage_trade logic for SL/TP exit.
        """
        # print(f"Row attributes: {dir(row)}")
        sl_pct = 0.05
        tp_pct = 0.10
        
        # Use col_name.lower() or just check what is available.
        # Based on error, it seems 'Close' is not in row.
        # Try accessing it as attribute maybe?
        
        # Actually, let's just use the column names that DO exist.
        # row is _Bar. Let's look at what's in _Bar.
        
        high = row.High if hasattr(row, 'High') else row.high
        low = row.Low if hasattr(row, 'Low') else row.low
        
        if position > 0:  # Long
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
            if low  <= sl_price: return 'SL', sl_price
            if high >= tp_price: return 'TP', tp_price
        elif position < 0:  # Short
            sl_price = entry_price * (1 + sl_pct)
            tp_price = entry_price * (1 - tp_pct)
            if high >= sl_price: return 'SL', sl_price
            if low  <= tp_price: return 'TP', tp_price
        
        return 'HOLD', None
