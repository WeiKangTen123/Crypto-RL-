"""
Dynamic VWAP ATR Scalper
==============================================================================
Fades overextensions from daily VWAP using ATR bands. When price deviates
more than N×ATR from VWAP, RSI is extreme, and volume confirms exhaustion,
enter counter-trend expecting a snap-back to VWAP.

Entry:
  Long : price <= VWAP - (atr_multiplier × ATR)  AND  RSI < rsi_oversold
          AND volume > vol_sma × vol_multiplier
  Short: price >= VWAP + (atr_multiplier × ATR)  AND  RSI > rsi_overbought
          AND volume > vol_sma × vol_multiplier

Exit:
  TP: price reaches VWAP (snap-back target)
  SL: ATR-based (atr_multiplier_sl × ATR beyond entry), intrabar
  Max hold bars backstop
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy


class DynamicVWAPATRScalperStrategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'atr_period', 'atr_multiplier', 'rsi_period',
        'rsi_oversold', 'rsi_overbought', 'vol_ma_period', 'vol_multiplier', 'mode',
    })

    OPTIMIZATION_RANGES = {
        'atr_period':        (5,  30),
        'atr_multiplier':    (1.0, 4.0),
        'rsi_period':        (5,  30),
        'rsi_oversold':      (20, 40),
        'rsi_overbought':    (60, 80),
        'vol_ma_period':     (10, 50),
        'vol_multiplier':    (1.0, 3.0),
        'atr_multiplier_sl': (0.5, 3.0),
        'max_hold_bars':     (6,  72),
        'mode':              ['reversion', 'momentum'],
    }

    def __init__(
        self,
        df: pd.DataFrame,
        atr_period: int = 17,
        atr_multiplier: float = 3.996,
        rsi_period: int = 26,
        rsi_oversold: float = 32.462,
        rsi_overbought: float = 76.2612,
        vol_ma_period: int = 23,
        vol_multiplier: float = 1.5044,
        atr_multiplier_sl: float = 0.912,
        max_hold_bars: Optional[int] = 33,
        mode: str = 'reversion',
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.vol_ma_period = vol_ma_period
        self.vol_multiplier = vol_multiplier
        self.atr_multiplier_sl = atr_multiplier_sl
        self.max_hold_bars = max_hold_bars
        self.mode = mode

        self._s = {
            1:  dict(count=0, entry_price=None, sl_price=None),
            -1: dict(count=0, entry_price=None, sl_price=None),
        }
        self._atr_arr = None
        self._vwap_arr = None
        self._bar_index_map = {}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # 1. Daily VWAP (UTC reset)
        tp = (high + low + close) / 3.0
        dates = df.index.date
        df['_cumtpv'] = (tp * volume).groupby(dates).cumsum()
        df['_cumvol'] = volume.groupby(dates).cumsum()
        vwap = df['_cumtpv'] / df['_cumvol'].replace(0, np.nan)
        df['vwap'] = vwap
        self._vwap_arr = vwap.values

        # 2. ATR
        atr = ta.volatility.AverageTrueRange(
            high, low, close, window=self.atr_period
        ).average_true_range()
        df['atr'] = atr
        self._atr_arr = atr.values

        # 3. RSI
        rsi = ta.momentum.rsi(close, window=self.rsi_period)
        df['rsi'] = rsi

        # 4. Volume spike
        vol_sma = volume.rolling(window=self.vol_ma_period).mean()
        vol_spike = volume > (vol_sma * self.vol_multiplier)

        # 5. Entry conditions
        band_lower = vwap - (self.atr_multiplier * atr)
        band_upper = vwap + (self.atr_multiplier * atr)

        if self.mode == 'momentum':
            # Follow the momentum: enter in direction of deviation from VWAP
            long_cond  = (close >= band_upper) & (rsi > 50) & vol_spike
            short_cond = (close <= band_lower) & (rsi < 50) & vol_spike
        else:
            # reversion (default): fade overextensions back to VWAP
            long_cond  = (close <= band_lower) & (rsi < self.rsi_oversold) & vol_spike
            short_cond = (close >= band_upper) & (rsi > self.rsi_overbought) & vol_spike

        # Rising edge
        long_edge = long_cond & ~long_cond.shift(1).fillna(False)
        short_edge = short_cond & ~short_cond.shift(1).fillna(False)

        signals = np.zeros(len(df), dtype=int)
        signals[long_edge.values] = 1
        signals[short_edge.values] = -1

        df['signal'] = signals
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}
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

        side = int(np.sign(position))
        s = self._s[side]
        bar_idx = self._bar_index_map.get(row.name, -1)

        if entry_price != s['entry_price']:
            atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0
            s.update(
                count=0,
                entry_price=entry_price,
                sl_price=entry_price - side * (self.atr_multiplier_sl * atr),
            )

        s['count'] += 1

        vwap = self._vwap_arr[bar_idx] if bar_idx >= 0 else None
        vwap_valid = vwap is not None and not np.isnan(vwap)

        if side == 1:
            if float(row['Low']) <= s['sl_price']: return 'SL', s['sl_price']
            if vwap_valid and float(row['High']) >= vwap: return 'TP', vwap
        else:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']
            if vwap_valid and float(row['Low']) <= vwap: return 'TP', vwap

        if self.max_hold_bars is not None and s['count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
