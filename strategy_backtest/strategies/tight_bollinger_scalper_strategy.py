import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr


class TightBollingerScalperStrategy(BaseStrategy):
    """
    Tight Bollinger Band Scalper — mean reversion using tight bands (1.5 std).
    Entry only when price closes outside band THEN closes back inside.
    EMA-200 slope filter avoids trending markets.
    TP at BB midline; SL at ATR multiple.

    Factor Card: factor_library/Mean_Reversion/20260526_tight_bollinger_scalper.md
    Registered IDs: 187 (BTC/1h)

    Logic:
      - Long:  prev bar closed below lower BB, current bar closes back inside
               AND EMA-200 slope < ema_slope_thresh (flat market)
      - Short: prev bar closed above upper BB, current bar closes back inside
      - TP:    price reaches BB midline (SMA)
      - SL:    ATR × sl_atr_mult from entry
    """

    SIGNAL_PARAMS = frozenset(['bb_period', 'bb_std', 'ema_period', 'ema_slope_thresh'])

    OPTIMIZATION_RANGES = {
        'bb_period':        (10, 30),
        'bb_std':           (1.0, 2.0),
        'ema_period':       (100, 300),
        'ema_slope_thresh': (0.001, 0.010),
        'atr_period':       (7, 21),
        'sl_atr_mult':      (1.0, 3.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 17,
        bb_std: float = 1.9507,
        ema_period: int = 247,
        ema_slope_thresh: float = 0.0064,
        atr_period: int = 9,
        sl_atr_mult: float = 1.312,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.bb_period        = int(bb_period)
        self.bb_std           = float(bb_std)
        self.ema_period       = int(ema_period)
        self.ema_slope_thresh = float(ema_slope_thresh)
        self.atr_period       = int(atr_period)
        self.sl_atr_mult      = float(sl_atr_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df    = self.df.copy()
        close = df['Close']

        upper, mid, lower = talib.BBANDS(
            close, timeperiod=self.bb_period,
            nbdevup=self.bb_std, nbdevdn=self.bb_std,
        )
        df['bb_upper'] = upper
        df['bb_mid']   = mid
        df['bb_lower'] = lower
        df['atr']      = calc_atr(df, self.atr_period)

        ema = talib.EMA(close, timeperiod=self.ema_period)
        # Normalised slope: (ema - ema[5]) / ema[5]
        ema_slope = (ema - ema.shift(5)) / (ema.shift(5) + 1e-10)
        flat_ema  = ema_slope.abs() < self.ema_slope_thresh

        prev_close = close.shift(1)
        prev_upper = df['bb_upper'].shift(1)
        prev_lower = df['bb_lower'].shift(1)

        # Closed outside last bar, back inside this bar
        closed_back_long  = (prev_close < prev_lower) & (close >= lower)
        closed_back_short = (prev_close > prev_upper) & (close <= upper)

        long_cond  = closed_back_long  & flat_ema
        short_cond = closed_back_short & flat_ema

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

        sl  = s['sl_price']
        mid = float(row['bb_mid'])

        if side == 1:
            if float(row['Low']) <= sl:
                return 'SL', sl
            if float(row['High']) >= mid:
                return 'TP', mid
        else:
            if float(row['High']) >= sl:
                return 'SL', sl
            if float(row['Low']) <= mid:
                return 'TP', mid

        return 'HOLD', None
