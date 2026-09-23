import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os


# Ensure BaseStrategy can be imported

from strategy_backtest.base_strategy import BaseStrategy

class ETHLayeredReversionStrategy(BaseStrategy):
    """
    ETH Layered Mean Reversion Strategy (Contrarian Scalper).
    
    Logic:
      1. Initial Entry: Price reaches deviation threshold L1 (VWAP + ATR Band).
      2. Layering:decide to 'ADD' in manage_trade if price reaches L2 or L3.
      3. Dynamic Average: Engine tracks average entry price.
      4. Exit: Close at target (relative to Avg Price) or Hard Stop.
    """

    OPTIMIZATION_RANGES = {
        'atr_period':       (5,    30),
        'multiplier_l1':    (1.0,  10.0),
        'multiplier_l2':    (1.0,  15.0),
        'multiplier_l3':    (1.0,  15.0),
        'tp_pct':           (0.01, 0.15),
        'sl_pct':           (0.01, 0.10),
        'rsi_period':       (5,    30),
        'rsi_oversold':     (20,   40),
        'rsi_overbought':   (60,   85),
        'entry_mode':       ['LAYERED', 'SINGLE'],
    }

    SIGNAL_PARAMS = frozenset([
        'atr_period', 'multiplier_l1', 'multiplier_l2', 'multiplier_l3',
        'rsi_period', 'rsi_oversold', 'rsi_overbought', 'entry_mode',
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        atr_period: int = 13,
        multiplier_l1: float = 6.2898,
        multiplier_l2: float = 7.2477,
        multiplier_l3: float = 1.5001,
        tp_pct: float = 0.0882,
        sl_pct: float = 0.0866,
        rsi_period: int = 26,
        rsi_oversold: float = 35.57,
        rsi_overbought: float = 79.96,
        entry_mode: str = 'SINGLE',
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.atr_period = atr_period
        self.multiplier_l1 = multiplier_l1
        self.multiplier_l2 = multiplier_l2
        self.multiplier_l3 = multiplier_l3
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.entry_mode = entry_mode

        # State management for layering (per-side)
        self._s = {
            1:  dict(layers=0, entry_price=0.0),
            -1: dict(layers=0, entry_price=0.0),
        }
        self._last_qty = {1: 0.0, -1: 0.0}  # tracks position qty to detect post-liquidation resets

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # 1. VWAP (Daily UTC reset)
        tp = (high + low + close) / 3.0
        tp_v = tp * volume
        
        # Correct UTC Daily Reset: Reset whenever the date changes
        dates = df.index.date
        df['_cumtpv'] = tp_v.groupby(dates).cumsum()
        df['_cumvol'] = volume.groupby(dates).cumsum()
        df['vwap'] = df['_cumtpv'] / df['_cumvol'].replace(0, np.nan)

        # 2. ATR
        atr_obj = ta.volatility.AverageTrueRange(high, low, close, window=self.atr_period)
        df['atr'] = atr_obj.average_true_range()

        # 3. RSI
        df['rsi'] = ta.momentum.rsi(close, window=self.rsi_period)

        # 4. Entry Bands
        df['l1_upper'] = df['vwap'] + self.multiplier_l1 * df['atr']
        df['l1_lower'] = df['vwap'] - self.multiplier_l1 * df['atr']
        df['l2_upper'] = df['vwap'] + self.multiplier_l2 * df['atr']
        df['l2_lower'] = df['vwap'] - self.multiplier_l2 * df['atr']
        df['l3_upper'] = df['vwap'] + self.multiplier_l3 * df['atr']
        df['l3_lower'] = df['vwap'] - self.multiplier_l3 * df['atr']

        # Initial Entry Signal (Level 1)
        short_signal = (close >= df['l1_upper']) | (df['rsi'] >= self.rsi_overbought)
        long_signal = (close <= df['l1_lower']) | (df['rsi'] <= self.rsi_oversold)

        signals = np.zeros(len(df), dtype=int)
        signals[long_signal] = 1
        signals[short_signal] = -1

        df['signal'] = signals
        return df

    def manage_trade(self, row, position, avg_entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side     = int(np.sign(position))
        s        = self._s[side]
        curr_qty = abs(position)
        curr_price = float(row['Close'])

        # Detect post-liquidation: layers > 1 means we expected a larger position,
        # but qty dropped back to a single lot — external close happened, reset state.
        if s['layers'] > 1 and curr_qty < self._last_qty[side] * 0.9:
            s['layers']      = 0
            s['entry_price'] = 0.0
        self._last_qty[side] = curr_qty

        # Detect new trade or reset
        if s['layers'] == 0:
            s['entry_price'] = avg_entry_price
            s['layers'] = 1

        sl_price = avg_entry_price * (1.0 - side * self.sl_pct)
        tp_price = avg_entry_price * (1.0 + side * self.tp_pct)
        vwap = float(row['vwap'])

        if side == 1:
            tp_val = max(tp_price, vwap)
            if float(row['Low']) <= sl_price:
                s['layers'] = 0; s['entry_price'] = 0.0; return 'SL', sl_price
            if float(row['High']) >= tp_val:
                s['layers'] = 0; s['entry_price'] = 0.0; return 'TP', tp_val
        else:
            tp_val = min(tp_price, vwap)
            if float(row['High']) >= sl_price:
                s['layers'] = 0; s['entry_price'] = 0.0; return 'SL', sl_price
            if float(row['Low']) <= tp_val:
                s['layers'] = 0; s['entry_price'] = 0.0; return 'TP', tp_val

        # 3. Layering Logic — only in LAYERED mode
        if self.entry_mode == 'LAYERED':
            if s['layers'] == 1:
                l2_thresh = float(row['l2_lower']) if side == 1 else float(row['l2_upper'])
                if (side == 1 and curr_price <= l2_thresh) or (side == -1 and curr_price >= l2_thresh):
                    s['layers'] = 2
                    return 'ADD', None

            elif s['layers'] == 2:
                l3_thresh = float(row['l3_lower']) if side == 1 else float(row['l3_upper'])
                if (side == 1 and curr_price <= l3_thresh) or (side == -1 and curr_price >= l3_thresh):
                    s['layers'] = 3
                    return 'ADD', None

        return 'HOLD', None
