"""
RWA Momentum Strategy
==============================================================================
Adapted from the RWA Momentum INJ concept. Since INJ data is not available in
the local dataset, the strategy is implemented on BTC/ETH/BNB/SOL/XRP.

Logic:
1. Trend Filter: Price above EMA(50) AND EMA(200) — confirmed uptrend.
2. Consolidation Detection: ATR has been contracting (current ATR < ATR SMA).
3. Breakout Entry:
   - LONG: Close breaks above the highest high of the last `breakout_lookback` bars.
   - Volume confirms: current volume > vol_ma_period SMA × vol_multiplier.
4. Momentum Gate: RSI(14) between 50 and overbought threshold — strong but not exhausted.
5. Short entries mirror the same logic in reverse (below both EMAs, break of lowest low).

Exit:
   - ATR-based Take Profit: entry ± (tp_atr_mult × ATR)
   - ATR-based Stop Loss: entry ∓ (sl_atr_mult × ATR)
   - Max hold bars backstop.
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy


class RWAMomentumStrategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'ema_fast', 'ema_slow', 'breakout_lookback',
        'vol_ma_period', 'vol_multiplier',
        'rsi_period', 'rsi_min', 'rsi_max',
        'atr_contraction_period',
    })

    def __init__(
        self,
        df: pd.DataFrame,
        ema_fast: int = 25,
        ema_slow: int = 124,
        breakout_lookback: int = 20,
        vol_ma_period: int = 45,
        vol_multiplier: float = 1.8744,
        rsi_period: int = 16,
        rsi_min: float = 50.0,
        rsi_max: float = 75.0,
        atr_period: int = 21,
        atr_contraction_period: int = 20,
        tp_atr_mult: float = 5.9532,
        sl_atr_mult: float = 2.5874,
        max_hold_bars: Optional[int] = 188,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.breakout_lookback = breakout_lookback
        self.vol_ma_period = vol_ma_period
        self.vol_multiplier = vol_multiplier
        self.rsi_period = rsi_period
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.atr_period = atr_period
        self.atr_contraction_period = atr_contraction_period
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_bars = max_hold_bars

        self._s = {
            1:  dict(count=0, entry_price=None, sl_price=None, tp_price=None),
            -1: dict(count=0, entry_price=None, sl_price=None, tp_price=None),
        }
        self._atr_arr = None
        self._bar_index_map = {}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # 1. Trend EMAs
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        df['ema_fast'] = ema_fast
        df['ema_slow'] = ema_slow

        trend_up = (close > ema_fast) & (close > ema_slow)
        trend_down = (close < ema_fast) & (close < ema_slow)

        # 2. ATR and consolidation detection
        atr_ind = ta.volatility.AverageTrueRange(high, low, close, window=self.atr_period)
        atr = atr_ind.average_true_range()
        atr_sma = atr.rolling(window=self.atr_contraction_period).mean()
        contracting = atr < atr_sma
        df['atr'] = atr
        self._atr_arr = atr.values

        # 3. Breakout levels
        highest_high = high.shift(1).rolling(window=self.breakout_lookback).max()
        lowest_low = low.shift(1).rolling(window=self.breakout_lookback).min()
        breakout_long = close > highest_high
        breakout_short = close < lowest_low

        # 4. Volume spike
        vol_sma = volume.rolling(window=self.vol_ma_period).mean()
        vol_spike = volume > (vol_sma * self.vol_multiplier)

        # 5. RSI gate
        rsi = ta.momentum.rsi(close, window=self.rsi_period)
        df['rsi'] = rsi
        rsi_long_ok = (rsi >= self.rsi_min) & (rsi <= self.rsi_max)
        rsi_short_ok = (rsi <= (100 - self.rsi_min)) & (rsi >= (100 - self.rsi_max))

        # 6. Entry signals — rising edge only
        long_cond = trend_up & contracting & breakout_long & vol_spike & rsi_long_ok
        short_cond = trend_down & contracting & breakout_short & vol_spike & rsi_short_ok

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
                sl_price=entry_price - side * (self.sl_atr_mult * atr),
                tp_price=entry_price + side * (self.tp_atr_mult * atr),
            )

        s['count'] += 1

        if side == 1:
            if float(row['Low'])  <= s['sl_price']: return 'SL', s['sl_price']

            if float(row['High']) >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']

            if float(row['Low'])  <= s['tp_price']: return 'TP', s['tp_price']

        # Max hold backstop
        if self.max_hold_bars is not None and s['count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
