import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_adx


class BarStrengthMomentumStrategy(BaseStrategy):
    """
    Bar Strength Momentum — adapted from WorldQuant Alpha#53.

    Bar Strength measures how close the closing price is to the centre of the bar:
        bar_strength = (2*close - high - low) / (high - low)   # range -1 to +1
        +1 = close at the high (full bullish bar)
        -1 = close at the low  (full bearish bar)

    The strategy tracks the N-bar change in bar strength:
        bs_delta = bar_strength - bar_strength.shift(bs_period)

    A rising bs_delta (bars closing progressively higher within their range) signals
    building intrabar momentum → Long entry.
    A falling bs_delta signals deteriorating intrabar momentum → Short entry.

    An ADX filter gates out choppy markets where bar strength has no directional
    persistence.

    Factor Card: factor_library/Trend_Momentum/ (new)
    Registered IDs: 190 (BTC/4h)

    Source: WorldQuant 101 Formulaic Alphas — Alpha#53 (Kakushadze 2015)
    """

    SIGNAL_PARAMS = frozenset(['bs_period', 'entry_threshold', 'adx_period', 'adx_threshold'])

    OPTIMIZATION_RANGES = {
        'bs_period':       (5, 25),
        'entry_threshold': (0.1, 0.6),
        'adx_period':      (7, 21),
        'adx_threshold':   (15, 40),
        'atr_period':      (7, 21),
        'sl_atr_mult':     (1.0, 3.0),
        'atr_trail_mult':  (2.0, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        bs_period: int = 11,
        entry_threshold: float = 0.2657,
        adx_period: int = 13,
        adx_threshold: float = 32.3649,
        atr_period: int = 7,
        sl_atr_mult: float = 2.2915,
        atr_trail_mult: float = 4.9986,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.bs_period       = int(bs_period)
        self.entry_threshold = float(entry_threshold)
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
        close = df['Close'].astype(float)
        high  = df['High'].astype(float)
        low   = df['Low'].astype(float)

        hl_range     = (high - low).clip(lower=1e-8)
        bar_strength = (2.0 * close - high - low) / hl_range
        bs_delta     = bar_strength - bar_strength.shift(self.bs_period)

        adx    = talib.ADX(high, low, close, timeperiod=self.adx_period)
        adx_ok = adx > self.adx_threshold

        df['bs_delta'] = bs_delta
        df['atr']      = calc_atr(df, self.atr_period)

        long_cond  = (bs_delta >  self.entry_threshold) & adx_ok
        short_cond = (bs_delta < -self.entry_threshold) & adx_ok

        df['signal'] = 0
        df.loc[long_cond,  'signal'] = 1
        df.loc[short_cond, 'signal'] = -1

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

        # ATR trailing stop ratchet
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
