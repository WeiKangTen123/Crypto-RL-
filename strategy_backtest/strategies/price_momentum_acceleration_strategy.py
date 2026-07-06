import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_zscore


class PriceMomentumAccelerationStrategy(BaseStrategy):
    """
    Price Momentum Acceleration — adapted from WorldQuant Alpha#46.

    Computes the 2nd-order price difference (acceleration of momentum):
        accel_pct = (close + close_slow - 2 * close_fast) / close

    A positive value means price is decelerating from a fall (or still accelerating up).
    A negative value means price is decelerating from a rise (or still accelerating down).
    This is normalised via a rolling z-score to produce a dimensionless signal.

    Entry (contrarian, fade momentum extremes):
      Long  : z-score < -entry_threshold  (momentum was strongly downward, now slowing)
      Short : z-score >  entry_threshold  (momentum was strongly upward, now slowing)

    Factor Card: factor_library/Volatility_Breakout/ (new)
    Registered IDs: 189 (ETH/1h)

    Source: WorldQuant 101 Formulaic Alphas — Alpha#46 (Kakushadze 2015)
    """

    SIGNAL_PARAMS = frozenset(['fast_period', 'slow_period', 'zscore_period', 'entry_threshold'])

    OPTIMIZATION_RANGES = {
        'fast_period':     (5, 20),
        'slow_period':     (15, 40),
        'zscore_period':   (50, 200),
        'entry_threshold': (1.0, 3.0),
        'atr_period':      (7, 21),
        'sl_atr_mult':     (1.0, 3.0),
        'atr_trail_mult':  (2.0, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        fast_period: int = 5,
        slow_period: int = 39,
        zscore_period: int = 150,
        entry_threshold: float = 2.7866,
        atr_period: int = 8,
        sl_atr_mult: float = 2.506,
        atr_trail_mult: float = 5.0669,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.fast_period     = int(fast_period)
        self.slow_period     = int(slow_period)
        self.zscore_period   = int(zscore_period)
        self.entry_threshold = float(entry_threshold)
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

        # 2nd-order price difference (% of close)
        close_fast = close.shift(self.fast_period)
        close_slow = close.shift(self.slow_period)
        accel_pct  = (close + close_slow - 2.0 * close_fast) / close.replace(0, np.nan)

        # Rolling z-score to normalise across volatility regimes
        accel_z = calc_zscore(accel_pct, self.zscore_period)

        df['accel_z'] = accel_z
        df['atr']     = calc_atr(df, self.atr_period)

        long_cond  = accel_z < -self.entry_threshold
        short_cond = accel_z >  self.entry_threshold

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
