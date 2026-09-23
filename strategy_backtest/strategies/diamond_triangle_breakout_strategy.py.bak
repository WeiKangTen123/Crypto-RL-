import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_bollinger_bands


class DiamondTriangleBreakoutStrategy(BaseStrategy):
    """
    Diamond Triangle Breakout — BB squeeze resolves into volume-confirmed
    breakout filtered by ADX trend strength. ATR trailing stop exit.

    Factor Card: factor_library/Volatility_Breakout/20260526_diamond_triangle_breakout.md
    Registered IDs: 184 (BTC/4h)

    Logic:
      - Detect squeeze: BB width < squeeze_pct of price for squeeze_bars consecutive bars
      - Long:  price breaks above upper BB + volume spike + ADX > threshold
      - Short: price breaks below lower BB + volume spike + ADX > threshold
      - Exit:  ATR trailing stop (3× ATR) or fixed SL (1.5× ATR from entry)
    """

    SIGNAL_PARAMS = frozenset([
        'bb_period', 'bb_std', 'squeeze_pct', 'squeeze_bars',
        'vol_period', 'vol_spike_mult', 'adx_period', 'adx_threshold',
    ])

    OPTIMIZATION_RANGES = {
        'bb_period':       (10, 30),
        'bb_std':          (1.5, 3.0),
        'squeeze_pct':     (0.03, 0.10),
        'squeeze_bars':    (3, 10),
        'vol_period':      (10, 30),
        'vol_spike_mult':  (1.2, 2.5),
        'adx_period':      (7, 21),
        'adx_threshold':   (15, 40),
        'atr_period':      (7, 21),
        'sl_atr_mult':     (1.0, 3.0),
        'atr_trail_mult':  (2.0, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 13,
        bb_std: float = 1.5704,
        squeeze_pct: float = 0.0586,
        squeeze_bars: int = 3,
        vol_period: int = 27,
        vol_spike_mult: float = 1.4286,
        adx_period: int = 11,
        adx_threshold: float = 24.6852,
        atr_period: int = 8,
        sl_atr_mult: float = 2.0913,
        atr_trail_mult: float = 3.6772,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.bb_period       = int(bb_period)
        self.bb_std          = float(bb_std)
        self.squeeze_pct     = float(squeeze_pct)
        self.squeeze_bars    = int(squeeze_bars)
        self.vol_period      = int(vol_period)
        self.vol_spike_mult  = float(vol_spike_mult)
        self.adx_period      = int(adx_period)
        self.adx_threshold   = float(adx_threshold)
        self.atr_period      = int(atr_period)
        self.sl_atr_mult     = float(sl_atr_mult)
        self.atr_trail_mult  = float(atr_trail_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df    = self.df.copy()
        close = df['Close']

        upper, mid, lower = calc_bollinger_bands(df, self.bb_period, self.bb_std)
        df['bb_upper'] = upper
        df['bb_lower'] = lower
        df['bb_mid']   = mid
        df['atr']      = calc_atr(df, self.atr_period)

        bb_width    = (upper - lower) / (mid.replace(0, np.nan))
        in_squeeze  = bb_width < self.squeeze_pct
        squeeze_sum = in_squeeze.rolling(self.squeeze_bars).sum()
        # True if the previous bars were in squeeze (shift 1 for no look-ahead)
        was_squeezed = squeeze_sum.shift(1) >= self.squeeze_bars

        vol_ma    = talib.EMA(df['Volume'].astype(float), timeperiod=self.vol_period)
        vol_spike = df['Volume'] > (vol_ma * self.vol_spike_mult)

        adx    = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=self.adx_period)
        adx_ok = adx > self.adx_threshold

        bullish_break = (close > upper) & was_squeezed & vol_spike & adx_ok
        bearish_break = (close < lower) & was_squeezed & vol_spike & adx_ok

        df['signal'] = 0
        df.loc[bullish_break, 'signal'] = 1
        df.loc[bearish_break, 'signal'] = -1

        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s    = self._s[side]
        atr  = float(row['atr']) if row['atr'] > 0 else entry_price * 0.01

        if s['entry_price'] != entry_price:
            s['entry_price'] = entry_price
            s['sl_price']    = entry_price - side * (self.sl_atr_mult * atr)

        # Trail stop ratchet
        if side == 1:
            new_sl = float(row['High']) - self.atr_trail_mult * atr
            if new_sl > s['sl_price']:
                s['sl_price'] = new_sl
            if float(row['Low']) <= s['sl_price']:
                return 'SL', s['sl_price']
        else:
            new_sl = float(row['Low']) + self.atr_trail_mult * atr
            if new_sl < s['sl_price']:
                s['sl_price'] = new_sl
            if float(row['High']) >= s['sl_price']:
                return 'SL', s['sl_price']

        return 'HOLD', None
