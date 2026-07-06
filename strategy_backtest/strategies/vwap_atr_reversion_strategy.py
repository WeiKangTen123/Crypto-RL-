"""
VWAP Mean Reversion with ATR Volatility Bands
==============================================
Mean reversion around daily-reset VWAP using ATR-based distance bands,
candle-pattern confirmation, volume exhaustion filter, and EMA trend filter.

Long  : Close ≤ VWAP − mult×ATR + (Hammer|BullEngulf) + vol exhaustion + not trending
Short : Close ≥ VWAP + mult×ATR + (ShootingStar|BearEngulf) + vol exhaustion + not trending
TP    : Intrabar touch of VWAP
SL    : entry ± sl_multiplier × ATR  (fixed at entry)
Exit  : max_hold_bars time-based exit
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy


class VWAPATRReversionStrategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({'multiplier', 'atr_period', 'ema_slope_thresh',
                               'use_pattern_filter', 'use_vol_filter', 'exit_mode'})

    # Logic Switch Ranges for the Fine-Tuner
    OPTIMIZATION_RANGES = {
        'exit_mode':          ['VWAP_TOUCH', 'ATR_TRAILING'],
        'multiplier':         (0.3, 6.0),
        'sl_multiplier':      (0.5, 6.9),
        'atr_period':         (5, 100),
        'max_hold_bars':      (12, 750),
        'ema_slope_thresh':   (0.005, 0.50),
        'use_pattern_filter': [True, False],
        'use_vol_filter':     [True, False],
    }

    def __init__(
        self,
        df: pd.DataFrame,
        multiplier: float = 5.2412,
        sl_multiplier: float = 6.619,
        atr_period: int = 64,
        max_hold_bars: int = 262,
        ema_slope_thresh: float = 0.2363,
        use_pattern_filter: bool = True,
        use_vol_filter: bool = True,
        exit_mode: str = 'ATR_TRAILING',
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.multiplier          = multiplier
        self.sl_multiplier       = sl_multiplier
        self.atr_period          = atr_period
        self.max_hold_bars       = max_hold_bars
        self.ema_slope_thresh    = ema_slope_thresh
        self.use_pattern_filter  = use_pattern_filter
        self.use_vol_filter      = use_vol_filter
        self.exit_mode           = exit_mode

        self._s = {
            1:  dict(entry_price=None, sl_price=None, ts_price=None, bars_held=0),
            -1: dict(entry_price=None, sl_price=None, ts_price=None, bars_held=0),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    # ── generate_signals ────────────────────────────────────────────────────────
    def generate_signals(self) -> pd.DataFrame:
        df = self.df

        # ── VWAP (daily UTC reset) ───────────────────────────────────────────────
        tp    = (df['High'] + df['Low'] + df['Close']) / 3.0
        tp_v  = tp * df['Volume']
        dates = df.index.normalize()           # UTC midnight grouping

        df['_cumtpv'] = tp_v.groupby(dates).cumsum()
        df['_cumvol'] = df['Volume'].groupby(dates).cumsum()
        df['vwap']    = df['_cumtpv'] / df['_cumvol'].replace(0, np.nan)
        df.drop(columns=['_cumtpv', '_cumvol'], inplace=True)

        # ── ATR ──────────────────────────────────────────────────────────────────
        atr_obj = ta.volatility.AverageTrueRange(
            df['High'], df['Low'], df['Close'], window=self.atr_period
        )
        df['atr'] = atr_obj.average_true_range()

        # ── Bands ────────────────────────────────────────────────────────────────
        df['band_upper'] = df['vwap'] + self.multiplier * df['atr']
        df['band_lower'] = df['vwap'] - self.multiplier * df['atr']

        # ── Candle-pattern helpers ───────────────────────────────────────────────
        body   = (df['Close'] - df['Open']).abs()
        hi_oc  = df[['Open', 'Close']].max(axis=1)
        lo_oc  = df[['Open', 'Close']].min(axis=1)
        upper  = df['High'] - hi_oc
        lower  = lo_oc - df['Low']
        rng    = df['High'] - df['Low']
        has_body = body >= rng * 0.05          # not a doji

        hammer       = has_body & (lower >= 2 * body) & (upper <= body)
        shooting_star = has_body & (upper >= 2 * body) & (lower <= body)

        prev_close = df['Close'].shift(1)
        prev_open  = df['Open'].shift(1)
        bull_engulf = (
            (prev_open > prev_close) &
            (df['Close'] > df['Open']) &
            (df['Close'] > prev_open) &
            (df['Open'] < prev_close)
        )
        bear_engulf = (
            (prev_open < prev_close) &
            (df['Close'] < df['Open']) &
            (df['Close'] < prev_open) &
            (df['Open'] > prev_close)
        )

        # ── Volume exhaustion (current vol < all previous 3 bars) ────────────────
        v1 = df['Volume'].shift(1)
        v2 = df['Volume'].shift(2)
        v3 = df['Volume'].shift(3)
        vol_exhaust = (df['Volume'] < v1) & (df['Volume'] < v2) & (df['Volume'] < v3)

        # ── Trend/regime filter (EMA-200 slope over 5 bars as %) ────────────────
        ema200    = ta.trend.ema_indicator(df['Close'], window=200)
        ema_slope = ema200.pct_change(5).abs() * 100
        trending  = ema_slope > self.ema_slope_thresh

        # ── Entry signals ────────────────────────────────────────────────────────
        long_base  = (df['Close'] <= df['band_lower']) & ~trending
        short_base = (df['Close'] >= df['band_upper']) & ~trending

        if self.use_pattern_filter:
            long_base  = long_base  & (hammer | bull_engulf)
            short_base = short_base & (shooting_star | bear_engulf)

        if self.use_vol_filter:
            long_base  = long_base  & vol_exhaust
            short_base = short_base & vol_exhaust

        long_cond  = long_base
        short_cond = short_base

        signals = np.zeros(len(df), dtype=int)
        signals[long_cond.values]  =  1
        signals[short_cond.values] = -1
        df['signal'] = signals

        # Store arrays for manage_trade
        self._atr_arr  = df['atr'].values
        self._vwap_arr = df['vwap'].values

        return df

    # ── manage_trade ─────────────────────────────────────────────────────────────
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

        # Detect new trade (entry_price changed)
        if entry_price != s['entry_price']:
            atr_e = self._atr_arr[idx] if idx >= 0 else 0.0
            sl    = entry_price - side * self.sl_multiplier * atr_e
            s['entry_price'] = entry_price
            s['sl_price']    = sl
            s['ts_price']    = sl   # Initialize Trailing Stop at SL level
            s['bars_held']   = 0

        s['bars_held'] += 1

        sl   = s['sl_price']
        vwap = self._vwap_arr[idx] if idx >= 0 else 0.0
        atr  = self._atr_arr[idx] if idx >= 0 else 0.0

        if self.exit_mode == 'VWAP_TOUCH' and vwap > 0:
            if side == 1:
                if row['Low']  <= sl:   return 'SL', sl
                if row['High'] >= vwap: return 'TP', vwap
            else:
                if row['High'] >= sl:   return 'SL', sl
                if row['Low']  <= vwap: return 'TP', vwap
        elif self.exit_mode == 'ATR_TRAILING':
            if side == 1:
                if row['Low'] <= sl: return 'SL', sl
                new_ts = row['Close'] - (self.sl_multiplier * atr)
                s['ts_price'] = max(s['ts_price'], new_ts)
                if row['Low'] <= s['ts_price']: return 'TS', s['ts_price']
            else:
                if row['High'] >= sl: return 'SL', sl
                new_ts = row['Close'] + (self.sl_multiplier * atr)
                s['ts_price'] = min(s['ts_price'], new_ts)
                if row['High'] >= s['ts_price']: return 'TS', s['ts_price']
        else:
            if side == 1 and row['Low']  <= sl: return 'SL', sl
            if side == -1 and row['High'] >= sl: return 'SL', sl

        # 3. Time-based exit
        if s['bars_held'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
