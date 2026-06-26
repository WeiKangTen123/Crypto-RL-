"""
VWAP RSI Reversion
==================
Intraday mean reversion strategy that assumes price will snap back to the VWAP after an extreme deviation, confirmed by RSI extreme levels.

Long  : Close < VWAP * (1 - vwap_deviation_pct) + RSI < rsi_oversold + ADX < adx_thresh
Short : Close > VWAP * (1 + vwap_deviation_pct) + RSI > rsi_overbought + ADX < adx_thresh
TP    : Intrabar touch of VWAP
SL    : entry * (1 ± sl_pct)
Exit  : max_hold_bars time-based exit
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy


class VWAPRSIReversionStrategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({'vwap_deviation_pct', 'rsi_period', 'rsi_oversold', 'rsi_overbought',
                               'adx_period', 'adx_thresh', 'sl_pct', 'max_hold_bars'})

    def __init__(
        self,
        df: pd.DataFrame,
        vwap_deviation_pct: float = 0.02,
        rsi_period: int = 17,
        rsi_oversold: float = 36.8798,
        rsi_overbought: float = 75.8611,
        adx_period: int = 7,
        adx_thresh: float = 30.0,
        sl_pct: float = 0.1654,
        max_hold_bars: int = 158,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.vwap_deviation_pct = vwap_deviation_pct
        self.rsi_period         = rsi_period
        self.rsi_oversold       = rsi_oversold
        self.rsi_overbought     = rsi_overbought
        self.adx_period         = adx_period
        self.adx_thresh         = adx_thresh
        self.sl_pct             = sl_pct
        self.max_hold_bars      = max_hold_bars

        self._s = {
            1:  dict(entry_price=None, sl_price=None, bars_held=0),
            -1: dict(entry_price=None, sl_price=None, bars_held=0),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df

        # ── VWAP (daily UTC reset) ───────────────────────────────────────────────
        tp    = (df['High'] + df['Low'] + df['Close']) / 3.0
        tp_v  = tp * df['Volume']
        dates = df.index.normalize()

        df['_cumtpv'] = tp_v.groupby(dates).cumsum()
        df['_cumvol'] = df['Volume'].groupby(dates).cumsum()
        df['vwap']    = df['_cumtpv'] / df['_cumvol'].replace(0, np.nan)
        df.drop(columns=['_cumtpv', '_cumvol'], inplace=True)

        # ── RSI ──────────────────────────────────────────────────────────────────
        df['rsi'] = ta.momentum.rsi(df['Close'], window=self.rsi_period)

        # ── ADX ──────────────────────────────────────────────────────────────────
        adx_obj = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=self.adx_period)
        df['adx'] = adx_obj.adx()

        # ── Entry signals ────────────────────────────────────────────────────────
        long_base  = (df['Close'] < df['vwap'] * (1 - self.vwap_deviation_pct))
        short_base = (df['Close'] > df['vwap'] * (1 + self.vwap_deviation_pct))

        rsi_long  = df['rsi'] < self.rsi_oversold
        rsi_short = df['rsi'] > self.rsi_overbought

        adx_filter = df['adx'] < self.adx_thresh

        long_cond  = long_base & rsi_long & adx_filter
        short_cond = short_base & rsi_short & adx_filter

        signals = np.zeros(len(df), dtype=int)
        signals[long_cond.values]  =  1
        signals[short_cond.values] = -1
        df['signal'] = signals

        self._vwap_arr = df['vwap'].values

        return df

    def manage_trade(
        self,
        row: pd.Series,
        position: float,
        entry_price: float,
        wallet: float = 0.0,
    ) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s    = self._s[side]
        idx  = self._bar_index_map.get(row.name, -1)

        # Detect new trade
        if entry_price != s['entry_price']:
            sl = entry_price * (1 - side * self.sl_pct)
            s['entry_price'] = entry_price
            s['sl_price']    = sl
            s['bars_held']   = 0

        s['bars_held'] += 1

        sl   = s['sl_price']
        vwap = self._vwap_arr[idx] if idx >= 0 else 0.0

        if vwap > 0:
            if side == 1:
                if row['Low']  <= sl:   return 'SL', sl
                if row['High'] >= vwap: return 'TP', vwap
            else:
                if row['High'] >= sl:   return 'SL', sl
                if row['Low']  <= vwap: return 'TP', vwap
        else:
            if side == 1 and row['Low']  <= sl: return 'SL', sl
            if side == -1 and row['High'] >= sl: return 'SL', sl

        # 3. Time-based exit
        if s['bars_held'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
