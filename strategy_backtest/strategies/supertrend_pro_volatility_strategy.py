import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_supertrend, calc_atr, calc_rsi


class SupertrendProVolatilityStrategy(BaseStrategy):
    """
    Supertrend Pro Volatility Breakout — Supertrend flip filtered by
    Relative Volume (vol > rv_threshold × EMA) and RSI momentum zone.

    Factor Card: factor_library/Trend_Momentum/20260526_supertrend_pro_volatility.md
    Registered IDs: 183 (BTC/4h)

    Logic:
      - Long:  Supertrend flips bullish + RV > threshold + 50 < RSI < 70
      - Short: Supertrend flips bearish + RV > threshold + 30 < RSI < 50
      - Exit:  ATR trailing stop or Supertrend flip reversal
    """

    SIGNAL_PARAMS = frozenset(['st_period', 'st_multiplier', 'rv_period', 'rv_threshold', 'rsi_period'])

    OPTIMIZATION_RANGES = {
        'st_period':       (5, 20),
        'st_multiplier':   (1.5, 5.0),
        'rv_period':       (10, 50),
        'rv_threshold':    (1.0, 2.5),
        'rsi_period':      (7, 21),
        'atr_period':      (7, 21),
        'atr_trail_mult':  (1.5, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        st_period: int = 15,
        st_multiplier: float = 3.0438,
        rv_period: int = 37,
        rv_threshold: float = 1.5717,
        rsi_period: int = 14,
        atr_period: int = 13,
        atr_trail_mult: float = 4.6781,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.st_period      = int(st_period)
        self.st_multiplier  = float(st_multiplier)
        self.rv_period      = int(rv_period)
        self.rv_threshold   = float(rv_threshold)
        self.rsi_period     = int(rsi_period)
        self.atr_period     = int(atr_period)
        self.atr_trail_mult = float(atr_trail_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df    = self.df.copy()
        close = df['Close']

        st_line, st_dir = calc_supertrend(df, self.st_period, self.st_multiplier)
        df['st_line'] = st_line
        df['st_dir']  = st_dir
        df['atr']     = calc_atr(df, self.atr_period)

        vol_ema = talib.EMA(df['Volume'].astype(float), timeperiod=self.rv_period)
        df['rv'] = df['Volume'] / (vol_ema + 1e-10)

        df['rsi'] = calc_rsi(close, self.rsi_period)

        prev_dir = df['st_dir'].shift(1)
        flip_up   = (df['st_dir'] == 1)  & (prev_dir == -1)
        flip_down = (df['st_dir'] == -1) & (prev_dir == 1)

        vol_ok = df['rv'] > self.rv_threshold
        long_cond  = flip_up   & vol_ok & (df['rsi'] > 50) & (df['rsi'] < 70)
        short_cond = flip_down & vol_ok & (df['rsi'] > 30) & (df['rsi'] < 50)

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
            s['sl_price']    = entry_price - side * (self.atr_trail_mult * atr)

        # Trail stop
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

        # Supertrend flip reversal exit
        st_dir = int(row['st_dir'])
        if (side == 1 and st_dir == -1) or (side == -1 and st_dir == 1):
            return 'EXIT', None

        return 'HOLD', None
