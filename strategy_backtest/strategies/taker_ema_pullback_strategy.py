import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy


class TakerEMAPullbackStrategy(BaseStrategy):
    """
    Taker-EMA Pullback Strategy (Long-Only, 15m BTC)

    Edge hypothesis:
      During a pullback to the fast EMA, if taker-buy ratio stays elevated,
      aggressive buyers are absorbing offers — pullback is liquidity-driven,
      not a trend reversal. A bullish engulfing or pin-bar confirms the bounce.

    Entry (all conditions required):
      1. Close > EMA(ema_slow)                    — bullish macro trend
      2. Low <= EMA(ema_fast) and
         Close >= EMA(ema_fast) * (1 - touch_band) — price touched EMA but closed above
      3. avg taker_buy_ratio over last pullback_lookback bars >= taker_threshold
      4. Bullish engulfing OR hammer pin-bar on the touch candle

    Exit:
      SL  : intrabar Low <= SL price  OR  Close < EMA(ema_fast) * (1 - sl_pct)
      TP  : intrabar High >= TP price  (prev swing high OR entry + tp_rr × risk)
      Time: bars_held >= max_hold_bars
    """

    SIGNAL_PARAMS = frozenset([
        'ema_fast', 'ema_slow', 'taker_threshold', 'pullback_lookback',
        'sl_pct', 'touch_band', 'swing_lookback',
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        ema_fast: int = 5,
        ema_slow: int = 193,
        taker_threshold: float = 0.6405,
        pullback_lookback: int = 2,
        sl_pct: float = 0.1905,
        touch_band: float = 0.0028,
        tp_rr: float = 3.7837,
        swing_lookback: int = 28,
        max_hold_bars: int = 160,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.ema_fast        = ema_fast
        self.ema_slow        = ema_slow
        self.taker_threshold = taker_threshold
        self.pullback_lookback = pullback_lookback
        self.sl_pct          = sl_pct
        self.touch_band      = touch_band
        self.tp_rr           = tp_rr
        self.swing_lookback  = swing_lookback
        self.max_hold_bars   = max_hold_bars

        self._s = {1: dict(entry_price=0.0, sl_price=0.0, tp_price=0.0, bar_count=0)}

    # ── Pattern helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _bullish_engulfing(df: pd.DataFrame) -> pd.Series:
        po = df['Open'].shift(1)
        pc = df['Close'].shift(1)
        co = df['Open']
        cc = df['Close']
        return (
            (cc > co) &       # current candle is bullish
            (co <= pc) &      # opens at or below prev close
            (cc >= po)        # closes at or above prev open
        )

    @staticmethod
    def _hammer_pin_bar(df: pd.DataFrame) -> pd.Series:
        body         = (df['Close'] - df['Open']).abs().clip(lower=1e-10)
        lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        return (
            (lower_shadow >= 2.0 * body) &
            (upper_shadow <= body)
        )

    # ── Signal generation ────────────────────────────────────────────────────
    def generate_signals(self) -> pd.DataFrame:
        df   = self.df
        close  = df['Close']
        high   = df['High']
        low    = df['Low']
        volume = df['Volume']
        taker  = df['taker_buy_base_vol']

        # EMAs
        df['_ema_fast'] = ta.trend.ema_indicator(close, window=self.ema_fast)
        df['_ema_slow'] = ta.trend.ema_indicator(close, window=self.ema_slow)

        # Taker ratio — rolling average over pullback window
        df['_taker_ratio']     = taker / (volume + 1e-10)
        df['_taker_ratio_avg'] = df['_taker_ratio'].rolling(window=self.pullback_lookback).mean()

        # Swing reference levels (shifted so no lookahead)
        df['_swing_low']  = low.rolling(window=self.swing_lookback).min().shift(1)
        df['_swing_high'] = high.rolling(window=self.swing_lookback).max().shift(1)

        # Candle patterns
        df['_pattern'] = self._bullish_engulfing(df) | self._hammer_pin_bar(df)

        # Entry conditions
        trend_ok   = close > df['_ema_slow']
        touch_ok   = (low  <= df['_ema_fast']) & \
                     (close >= df['_ema_fast'] * (1.0 - self.touch_band))
        taker_ok   = df['_taker_ratio_avg'] >= self.taker_threshold
        pattern_ok = df['_pattern']

        df['signal'] = 0
        df.loc[trend_ok & touch_ok & taker_ok & pattern_ok, 'signal'] = 1
        return df

    # ── Trade management ─────────────────────────────────────────────────────
    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        if side != 1:       # long-only
            return 'EXIT', None

        s = self._s[1]

        # Initialise on new trade
        if entry_price != s['entry_price']:
            s['entry_price'] = entry_price
            sl_pct_price = entry_price * (1.0 - self.sl_pct)
            swing_low    = float(row['_swing_low']) if not pd.isna(row['_swing_low']) else sl_pct_price
            s['sl_price'] = min(sl_pct_price, swing_low)
            risk          = entry_price - s['sl_price']
            tp_rr_price   = entry_price + self.tp_rr * risk
            swing_high    = float(row['_swing_high']) if not pd.isna(row['_swing_high']) else tp_rr_price
            s['tp_price'] = max(tp_rr_price, swing_high)
            s['bar_count'] = 0

        s['bar_count'] += 1
        sl    = s['sl_price']
        tp    = s['tp_price']
        ema_f = float(row['_ema_fast']) if not pd.isna(row['_ema_fast']) else 0.0

        ema_sl_breach = ema_f > 0 and float(row['Close']) < ema_f * (1.0 - self.sl_pct)
        intrabar_sl   = float(row['Low']) <= sl

        if intrabar_sl or ema_sl_breach: return 'SL', sl
        if float(row['High']) >= tp: return 'TP', tp

        # 3. Time exit
        if s['bar_count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None
