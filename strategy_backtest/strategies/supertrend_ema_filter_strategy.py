import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_supertrend, calc_atr


class SupertrendEmaFilterStrategy(BaseStrategy):
    """
    Supertrend Pro — Supertrend flip entry filtered by EMA-200 macro regime.

    Factor Card: factor_library/Trend_Momentum/20260527_supertrend_pro.md
    Registered IDs: 182 (BTC/4h)

    Logic:
      - Long:  Supertrend flips bearish→bullish (dir: -1 → +1) AND Close > EMA(ema_period)
      - Short: Supertrend flips bullish→bearish (dir: +1 → -1) AND Close < EMA(ema_period)
      - Exit:  ATR SL/TP or Supertrend flip back (signal reversal)
    """

    SIGNAL_PARAMS = frozenset([
        'st_period', 'st_multiplier', 'ema_period', 'use_ema_filter',
    ])

    OPTIMIZATION_RANGES = {
        'use_ema_filter':  [True, False],
        'st_period':       (5, 20),
        'st_multiplier':   (1.5, 5.0),
        'ema_period':      (100, 300),
        'atr_period':      (7, 21),
        'sl_atr_mult':     (0.5, 3.0),
        'tp_rr':           (1.5, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        st_period: int = 16,
        st_multiplier: float = 4.8708,
        ema_period: int = 177,
        atr_period: int = 13,
        sl_atr_mult: float = 1.8594,
        tp_rr: float = 1.8277,
        use_ema_filter: bool = True,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.st_period      = int(st_period)
        self.st_multiplier  = float(st_multiplier)
        self.ema_period     = int(ema_period)
        self.atr_period     = int(atr_period)
        self.sl_atr_mult    = float(sl_atr_mult)
        self.tp_rr          = float(tp_rr)
        self.use_ema_filter = bool(use_ema_filter)

        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close = df['Close']

        # 1. Supertrend
        st_line, st_dir = calc_supertrend(df, self.st_period, self.st_multiplier)
        df['st_line'] = st_line
        df['st_dir']  = st_dir

        # 2. EMA macro filter
        df['ema_macro'] = talib.EMA(close, timeperiod=self.ema_period)

        # 3. ATR for risk management
        df['atr'] = calc_atr(df, self.atr_period)

        # 4. Signal: Supertrend flip
        prev_dir = df['st_dir'].shift(1)
        flip_up   = (df['st_dir'] == 1)  & (prev_dir == -1)
        flip_down = (df['st_dir'] == -1) & (prev_dir == 1)

        if self.use_ema_filter:
            long_cond  = flip_up   & (close > df['ema_macro'])
            short_cond = flip_down & (close < df['ema_macro'])
        else:
            long_cond  = flip_up
            short_cond = flip_down

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

        # Reset state when a new trade starts
        if s['entry_price'] != entry_price:
            sl = entry_price - side * (self.sl_atr_mult * atr)
            tp = entry_price + side * (abs(entry_price - sl) * self.tp_rr)
            s.update(entry_price=entry_price, sl_price=sl, tp_price=tp)

        sl = s['sl_price']
        tp = s['tp_price']
        bullish_bar = float(row['Close']) >= float(row['Open'])

        # Check both SL and TP hit — use candle direction to determine which fired first
        if side == 1:
            sl_hit = float(row['Low'])  <= sl
            tp_hit = float(row['High']) >= tp
            if sl_hit and tp_hit:
                return ('SL', sl) if bullish_bar else ('TP', tp)
            if sl_hit: return 'SL', sl
            if tp_hit: return 'TP', tp
        else:
            sl_hit = float(row['High']) >= sl
            tp_hit = float(row['Low'])  <= tp
            if sl_hit and tp_hit:
                return ('TP', tp) if bullish_bar else ('SL', sl)
            if sl_hit: return 'SL', sl
            if tp_hit: return 'TP', tp

        # Signal exit: Supertrend flips against position
        st_dir = int(row['st_dir'])
        if (side == 1 and st_dir == -1) or (side == -1 and st_dir == 1):
            return 'EXIT', None

        return 'HOLD', None
