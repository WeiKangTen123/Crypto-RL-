"""
MACD + KDJ + ADX + ATR Strategy
==============================================================================
Enhanced version of MACDKDJStrategy with:
1. ADX Trend Strength Filter: Entries only allowed when ADX > threshold (e.g., 25).
2. ATR Dynamic Risk Management: Stop Loss and Take Profit levels based on volatility.

Logic:
Entry:
  Long: (MACDKDJ Long Signal) AND (ADX > adx_threshold)
  Short: (MACDKDJ Short Signal) AND (ADX > adx_threshold)

Exit:
  1. KDJ opposite cross (as in original)
  2. ATR-based Stop Loss: Entry Price - (atr_multiplier_sl * ATR)
  3. ATR-based Take Profit: Entry Price + (atr_multiplier_tp * ATR)
  4. Max hold time
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy


class MACDKDJ_ADX_ATR_Strategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'macd_fast', 'macd_slow', 'macd_signal',
        'kdj_period', 'kdj_oversold', 'kdj_overbought',
        'entry_window', 'trend_filter', 'trend_ema_period',
        'adx_period', 'adx_threshold'
    })

    OPTIMIZATION_RANGES = {
        'exit_mode':   ['FIXED_RR', 'TRAILING_STOP', 'KDJ_CROSS_ONLY'],
        'atr_multiplier_tp': (1.5, 10.0),
        'atr_multiplier_sl': (0.5, 4.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        macd_fast: int = 19,
        macd_slow: int = 25,
        macd_signal: int = 10,
        kdj_period: int = 24,
        kdj_oversold: float = 15.0,
        kdj_overbought: float = 82.0,
        entry_window: int = 16,
        trend_filter: bool = True,
        trend_ema_period: int = 215,
        adx_period: int = 17,
        adx_threshold: float = 29.7996,
        atr_period: int = 11,
        atr_multiplier_sl: float = 3.1631,
        atr_multiplier_tp: float = 6.3957,
        max_hold_bars: Optional[int] = 51,
        exit_mode: str = 'FIXED_RR',
        **kwargs,
    ):
        super().__init__(
            df,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            kdj_period=kdj_period,
            kdj_oversold=kdj_oversold,
            kdj_overbought=kdj_overbought,
            entry_window=entry_window,
            trend_filter=trend_filter,
            trend_ema_period=trend_ema_period,
            adx_period=adx_period,
            adx_threshold=adx_threshold,
            atr_period=atr_period,
            atr_multiplier_sl=atr_multiplier_sl,
            atr_multiplier_tp=atr_multiplier_tp,
            max_hold_bars=max_hold_bars,
            exit_mode=exit_mode,
            **kwargs,
        )
        self._s = {
            1:  dict(count=0, wallet=0.0, entry_price=None, sl_price=None, tp_price=None, ts_price=None),
            -1: dict(count=0, wallet=0.0, entry_price=None, sl_price=None, tp_price=None, ts_price=None),
        }
        self._kdj_death_arr  = None
        self._kdj_golden_arr = None
        self._atr_arr        = None
        self._bar_index_map  = {}

    def _compute_kdj(self, df: pd.DataFrame):
        low_min  = df['Low'].rolling(window=self.kdj_period, min_periods=1).min()
        high_max = df['High'].rolling(window=self.kdj_period, min_periods=1).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3.0 * K - 2.0 * D
        return K, D, J

    def generate_signals(self) -> pd.DataFrame:
        df = self.df

        # ── MACD ──────────────────────────────────────────────────────
        ema_fast    = df['Close'].ewm(span=self.macd_fast,   adjust=False).mean()
        ema_slow    = df['Close'].ewm(span=self.macd_slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal,  adjust=False).mean()
        macd_hist   = macd_line - signal_line

        # ── KDJ ───────────────────────────────────────────────────────
        K, D, J = self._compute_kdj(df)
        kdj_golden = (K > D) & (K.shift(1) <= D.shift(1))
        kdj_death  = (K < D) & (K.shift(1) >= D.shift(1))

        # ── ADX ───────────────────────────────────────────────────────
        adx_ind = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=self.adx_period)
        df['adx'] = adx_ind.adx()
        adx_strong = df['adx'] > self.adx_threshold

        # ── ATR ───────────────────────────────────────────────────────
        atr_ind = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=self.atr_period)
        df['atr'] = atr_ind.average_true_range()

        # ── MACD histogram sign flips ──────────────────────────────────
        macd_turn_pos = (macd_hist > 0) & (macd_hist.shift(1) <= 0)
        macd_turn_neg = (macd_hist < 0) & (macd_hist.shift(1) >= 0)

        # ── Trend filter (EMA) ─────────────────────────────────────────
        if self.trend_filter:
            ema_trend  = df['Close'].ewm(span=self.trend_ema_period, adjust=False).mean()
            trend_up   = df['Close'] > ema_trend
            trend_down = df['Close'] < ema_trend
        else:
            trend_up   = pd.Series(True,  index=df.index)
            trend_down = pd.Series(True,  index=df.index)

        # ── Entry signals ─────────────────────────────────────────────
        w = self.entry_window
        def _in_window(series):
            return series.astype(int).rolling(w, min_periods=1).max().fillna(0).astype(bool)

        long_ok = (
            _in_window(K < self.kdj_oversold)
            & _in_window(kdj_golden)
            & _in_window(macd_turn_pos)
            & trend_up
            & adx_strong
        )

        short_ok = (
            _in_window(K > self.kdj_overbought)
            & _in_window(kdj_death)
            & _in_window(macd_turn_neg)
            & trend_down
            & adx_strong
        )

        long_edge  = long_ok  & ~long_ok.shift(1, fill_value=False)
        short_edge = short_ok & ~short_ok.shift(1, fill_value=False)

        signals = np.zeros(len(df), dtype=int)
        signals[long_edge.values]  =  1
        signals[short_edge.values] = -1
        df['signal'] = signals

        self._kdj_death_arr  = kdj_death.values
        self._kdj_golden_arr = kdj_golden.values
        self._atr_arr        = df['atr'].values
        self._bar_index_map  = {ts: i for i, ts in enumerate(df.index)}

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
        s    = self._s[side]
        bar_idx = self._bar_index_map.get(row.name, -1)

        # Setup dynamic SL/TP on trade entry
        if entry_price != s['entry_price']:
            atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0
            sl_price = entry_price - side * (self.atr_multiplier_sl * atr)
            tp_price = entry_price + side * (self.atr_multiplier_tp * atr)
            s.update(count=0, wallet=wallet, entry_price=entry_price, sl_price=sl_price, tp_price=tp_price, ts_price=sl_price)

        s['count'] += 1
        kdj_death_now  = bool(self._kdj_death_arr[bar_idx])  if bar_idx >= 0 else False
        kdj_golden_now = bool(self._kdj_golden_arr[bar_idx]) if bar_idx >= 0 else False
        atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0

        # Exit mode logic with candle direction priority for SL vs TP
        if self.exit_mode == 'FIXED_RR':
            if side == 1:
                if row['Low']  <= s['sl_price']: return 'SL', s['sl_price']

                if row['High'] >= s['tp_price']: return 'TP', s['tp_price']
                if kdj_death_now: return 'EXIT', None
            else:
                if row['High'] >= s['sl_price']: return 'SL', s['sl_price']

                if row['Low']  <= s['tp_price']: return 'TP', s['tp_price']
                if kdj_golden_now: return 'EXIT', None

        elif self.exit_mode == 'TRAILING_STOP':
            if side == 1:
                if row['Low'] <= s['sl_price']: return 'SL', s['sl_price']
                s['ts_price'] = max(s['ts_price'], float(row['Close']) - self.atr_multiplier_sl * atr)
                if float(row['Low']) <= s['ts_price']: return 'TS', s['ts_price']
                if kdj_death_now: return 'EXIT', None
            else:
                if row['High'] >= s['sl_price']: return 'SL', s['sl_price']
                s['ts_price'] = min(s['ts_price'], float(row['Close']) + self.atr_multiplier_sl * atr)
                if float(row['High']) >= s['ts_price']: return 'TS', s['ts_price']
                if kdj_golden_now: return 'EXIT', None

        elif self.exit_mode == 'KDJ_CROSS_ONLY':
            if side == 1 and kdj_death_now:
                return 'EXIT', None
            if side == -1 and kdj_golden_now:
                return 'EXIT', None

        # 4. Max hold backstop
        if self.max_hold_bars is not None and s['count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
