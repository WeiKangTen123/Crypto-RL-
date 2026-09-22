"""
Donchian Channel Breakout Strategy
==============================================================================
Classic "Turtle Trader" breakout system adapted for BTC crypto markets.

Logic:
1. Donchian Channel: Upper = highest high of last N bars, Lower = lowest low,
   Middle = midpoint between upper and lower.
2. Entry (close-confirmed — no wick entries):
   - LONG : Close > Upper Band (new N-bar high)
   - SHORT: Close < Lower Band (new N-bar low)
3. Volume filter: volume must exceed vol_ma_period SMA × vol_multiplier
   (confirms genuine breakout, not a low-liquidity false move).
4. Exit:
   - ATR Take Profit : entry ± (tp_atr_mult × ATR)
   - ATR Stop Loss   : entry ∓ (atr_multiplier_sl × ATR), intrabar
   - Middle band exit: price crosses the Donchian midpoint on close
   - Max hold bars   : backstop force-close
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy


class DonchianBreakoutStrategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'lookback', 'vol_ma_period', 'vol_multiplier', 'atr_period',
        'adx_period', 'adx_threshold',
    })

    def __init__(
        self,
        df: pd.DataFrame,
        lookback: int = 7,
        vol_ma_period: int = 48,
        vol_multiplier: float = 1.6514,
        atr_period: int = 29,
        atr_multiplier_sl: float = 0.0032,
        tp_atr_mult: float = 7.6708,
        max_hold_bars: Optional[int] = 20,
        adx_period: int = 7,
        adx_threshold: float = 15.8315,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.lookback = lookback
        self.vol_ma_period = vol_ma_period
        self.vol_multiplier = vol_multiplier
        self.atr_period = atr_period
        self.atr_multiplier_sl = atr_multiplier_sl
        self.tp_atr_mult = tp_atr_mult
        self.max_hold_bars = max_hold_bars
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

        self._s = {
            1:  dict(count=0, entry_price=None, sl_price=None, tp_price=None),
            -1: dict(count=0, entry_price=None, sl_price=None, tp_price=None),
        }
        self._atr_arr = None
        self._dc_mid_arr = None
        self._bar_index_map = {}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # 1. Donchian Channel (shift(1) → use previous bars, no look-ahead)
        upper = high.shift(1).rolling(window=self.lookback).max()
        lower = low.shift(1).rolling(window=self.lookback).min()
        middle = (upper + lower) / 2.0
        df['dc_upper'] = upper
        df['dc_lower'] = lower
        df['dc_mid'] = middle

        # 2. Volume confirmation
        vol_sma = volume.rolling(window=self.vol_ma_period).mean()
        vol_ok = volume > (vol_sma * self.vol_multiplier)

        # 3. ATR for risk sizing
        atr = ta.volatility.AverageTrueRange(
            high, low, close, window=self.atr_period
        ).average_true_range()
        df['atr'] = atr
        self._atr_arr = atr.values
        self._dc_mid_arr = middle.values

        # 4. ADX regime filter — only enter when market is trending
        adx = ta.trend.ADXIndicator(
            high, low, close, window=self.adx_period
        ).adx()
        df['adx'] = adx
        trending = adx > self.adx_threshold

        # 5. Breakout signals — close confirmation only (no wick entries)
        long_cond = (close > upper) & vol_ok & trending
        short_cond = (close < lower) & vol_ok & trending

        # Rising edge — fire only on the first bar of the breakout
        long_edge = long_cond & ~long_cond.shift(1, fill_value=False)
        short_edge = short_cond & ~short_cond.shift(1, fill_value=False)

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
                tp_price=entry_price + side * (self.tp_atr_mult * atr),
            )

        s['count'] += 1

        # 1 & 2. SL/TP with candle direction
        if side == 1:
            if float(row['Low'])  <= s['sl_price']: return 'SL', s['sl_price']

            if float(row['High']) >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']

            if float(row['Low'])  <= s['tp_price']: return 'TP', s['tp_price']

        # 3. Middle band exit (close-based — trend exhaustion signal)
        dc_mid = self._dc_mid_arr[bar_idx] if bar_idx >= 0 else None
        if dc_mid is not None:
            curr_close = float(row['Close'])
            if side == 1 and curr_close < dc_mid:
                return 'EXIT', None
            if side == -1 and curr_close > dc_mid:
                return 'EXIT', None

        # 4. Max hold backstop
        if self.max_hold_bars is not None and s['count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
