"""
MACD + KDJ Strategy  (window-based entry / KDJ-cross exit / EMA trend filter)
==============================================================================
Signal logic based on 量化验证室 EP15 approach:

Entry — BOTH conditions must appear within `entry_window` bars of each other:
  Long  : (1) K < kdj_oversold  AND  K crosses above D  (golden cross)
           (2) MACD histogram turns negative → positive  (green bar → red bar)
  Short : (1) K > kdj_overbought  AND  K crosses below D  (death cross)
           (2) MACD histogram turns positive → negative  (red bar → green bar)

  The two conditions do NOT need to be on the same bar —
  they just both need to have occurred within the last `entry_window` bars.

Trend filter (optional, default ON):
  Long  entries only when Close > EMA(trend_ema_period)   — price in uptrend
  Short entries only when Close < EMA(trend_ema_period)   — price in downtrend
  Blocks counter-trend trades during strong bull/bear moves.

Exit — whichever fires first:
  1. KDJ opposite cross  : death cross (long exit)  /  golden cross (short exit)
  2. Price-based SL      : price moves stop_loss_pct% against entry price
  3. Max hold            : force-close after max_hold_bars bars

Parameters
----------
  macd_fast         : Fast EMA period                           (default 12)
  macd_slow         : Slow EMA period                           (default 26)
  macd_signal       : Signal line EMA period                    (default 9)
  kdj_period        : KDJ lookback window                       (default 9)
  kdj_oversold      : K threshold for long entry                (default 30)
  kdj_overbought    : K threshold for short entry               (default 70)
  stop_loss_pct     : Price-based SL — % from entry price       (default 0.05 = 0.0957%)
  take_profit_pct   : Optional TP from entry price              (default None)
  entry_window      : Bars to look back for both signals        (default 5)
  max_hold_bars     : Force-close after N bars (None = off)     (default 30)
  trend_filter      : Block counter-trend entries via EMA       (default True)
  trend_ema_period  : EMA period used for trend direction       (default 200)
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy


class MACDKDJStrategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'macd_fast', 'macd_slow', 'macd_signal',
        'kdj_period', 'kdj_oversold', 'kdj_overbought',
        'entry_window', 'trend_filter', 'trend_ema_period',
    })

    def __init__(
        self,
        df: pd.DataFrame,
        macd_fast: int = 18,
        macd_slow: int = 28,
        macd_signal: int = 16,
        kdj_period: int = 28,
        kdj_oversold: float = 38.0,
        kdj_overbought: float = 89.0,
        stop_loss_pct: float = 0.0957,
        take_profit_pct: Optional[float] = None,
        entry_window: int = 20,
        max_hold_bars: Optional[int] = 122,
        trend_filter: bool = True,
        trend_ema_period: int = 134,
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
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            entry_window=entry_window,
            max_hold_bars=max_hold_bars,
            trend_filter=trend_filter,
            trend_ema_period=trend_ema_period,
            **kwargs,
        )
        self._s = {
            1:  dict(count=0, wallet=0.0, entry_price=None),
            -1: dict(count=0, wallet=0.0, entry_price=None),
        }
        self._kdj_death_arr  = None
        self._kdj_golden_arr = None
        self._bar_index_map  = {}

    # ------------------------------------------------------------------
    @classmethod
    def validate_params(cls, params: dict) -> bool:
        if params.get('macd_fast', 1) >= params.get('macd_slow', 2):
            return False
        if params.get('kdj_oversold', 30) >= params.get('kdj_overbought', 70):
            return False
        return True

    # ------------------------------------------------------------------
    def _compute_kdj(self, df: pd.DataFrame):
        low_min  = df['Low'].rolling(window=self.kdj_period, min_periods=1).min()
        high_max = df['High'].rolling(window=self.kdj_period, min_periods=1).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3.0 * K - 2.0 * D
        return K, D, J

    # ------------------------------------------------------------------
    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # ── MACD ──────────────────────────────────────────────────────
        ema_fast    = df['Close'].ewm(span=self.macd_fast,   adjust=False).mean()
        ema_slow    = df['Close'].ewm(span=self.macd_slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal,  adjust=False).mean()
        macd_hist   = macd_line - signal_line

        df['macd_line']        = macd_line
        df['macd_signal_line'] = signal_line
        df['macd_hist']        = macd_hist

        # ── KDJ ───────────────────────────────────────────────────────
        K, D, J = self._compute_kdj(df)
        df['kdj_K'] = K
        df['kdj_D'] = D
        df['kdj_J'] = J

        kdj_golden = (K > D) & (K.shift(1) <= D.shift(1))
        kdj_death  = (K < D) & (K.shift(1) >= D.shift(1))
        df['kdj_golden'] = kdj_golden
        df['kdj_death']  = kdj_death

        # ── MACD histogram sign flips ──────────────────────────────────
        macd_turn_pos = (macd_hist > 0) & (macd_hist.shift(1) <= 0)
        macd_turn_neg = (macd_hist < 0) & (macd_hist.shift(1) >= 0)

        # ── Trend filter (EMA200) ──────────────────────────────────────
        if self.trend_filter:
            ema_trend  = df['Close'].ewm(span=self.trend_ema_period, adjust=False).mean()
            trend_up   = df['Close'] > ema_trend   # bullish regime
            trend_down = df['Close'] < ema_trend   # bearish regime
            df['ema_trend'] = ema_trend
        else:
            trend_up   = pd.Series(True,  index=df.index)
            trend_down = pd.Series(True,  index=df.index)

        # ── Entry signals: rolling window ─────────────────────────────
        w = self.entry_window

        def _in_window(series):
            return series.astype(int).rolling(w, min_periods=1).max().fillna(0).astype(bool)

        # Long: K oversold in window AND golden cross in window AND MACD flipped + in window
        long_ok = (
            _in_window(K < self.kdj_oversold)
            & _in_window(kdj_golden)
            & _in_window(macd_turn_pos)
            & trend_up                          # only in uptrend
        )

        # Short: K overbought in window AND death cross in window AND MACD flipped - in window
        short_ok = (
            _in_window(K > self.kdj_overbought)
            & _in_window(kdj_death)
            & _in_window(macd_turn_neg)
            & trend_down                        # only in downtrend
        )

        # Rising-edge: fire ONLY on the first bar where conditions become true.
        # Without this, the rolling window keeps firing for entry_window consecutive
        # bars, causing repeated entries after each quick exit.
        long_edge  = long_ok  & ~long_ok.shift(1).fillna(False)
        short_edge = short_ok & ~short_ok.shift(1).fillna(False)

        signals = np.zeros(len(df), dtype=int)
        signals[long_edge.values]  =  1
        signals[short_edge.values] = -1
        signals[long_edge.values & short_edge.values] = 1   # long priority

        df['signal'] = signals

        self._kdj_death_arr  = kdj_death.values
        self._kdj_golden_arr = kdj_golden.values
        self._bar_index_map  = {ts: i for i, ts in enumerate(df.index)}

        return df

    # ------------------------------------------------------------------
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

        if entry_price != s['entry_price']:
            s.update(count=0, wallet=wallet, entry_price=entry_price)

        s['count'] += 1

        bar_idx        = self._bar_index_map.get(row.name, -1)
        kdj_death_now  = bool(self._kdj_death_arr[bar_idx])  if bar_idx >= 0 else False
        kdj_golden_now = bool(self._kdj_golden_arr[bar_idx]) if bar_idx >= 0 else False

        # 1. Price-based stops with candle direction priority
        sl_price = entry_price * (1.0 - side * self.stop_loss_pct)   if self.stop_loss_pct   is not None else None
        tp_price = entry_price * (1.0 + side * self.take_profit_pct) if self.take_profit_pct is not None else None

        if sl_price is not None or tp_price is not None:
            if side == 1:
                if sl_price is not None and row['Low']  <= sl_price: return 'SL', sl_price
                if tp_price is not None and row['High'] >= tp_price: return 'TP', tp_price
            else:
                if sl_price is not None and row['High'] >= sl_price: return 'SL', sl_price
                if tp_price is not None and row['Low']  <= tp_price: return 'TP', tp_price

        # 3. KDJ opposite cross — primary exit signal
        if side == 1 and kdj_death_now:
            return 'EXIT', None
        if side == -1 and kdj_golden_now:
            return 'EXIT', None

        # 4. Max hold backstop
        if self.max_hold_bars is not None and s['count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
