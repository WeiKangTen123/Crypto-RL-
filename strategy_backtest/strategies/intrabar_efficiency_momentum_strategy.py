import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr


class IntrabarEfficiencyMomentumStrategy(BaseStrategy):
    """
    Intrabar Efficiency Momentum — adapted from WorldQuant Alpha#101.

    Alpha#101: (close - open) / (high - low + 0.001)

    Bar efficiency measures directional capture — how much of the full bar range
    was expressed as a net directional move:
        +1.0 = perfectly bullish (open at low, close at high)
        -1.0 = perfectly bearish (open at high, close at low)
         0.0 = indecisive (doji or wide-range reversal bar)

    A rolling average of bar efficiency detects when recent candles have been
    consistently directional. When smoothed efficiency exceeds a threshold AND
    price is above the EMA trend filter → momentum is intact → enter long.

    Long entry:  smooth_efficiency >  threshold AND close > EMA
    Short entry: smooth_efficiency < -threshold AND close < EMA

    Source: WorldQuant 101 Formulaic Alphas — Alpha#101 (Kakushadze 2015)
    """

    SIGNAL_PARAMS = frozenset(['smooth_period', 'entry_threshold', 'ema_period'])

    OPTIMIZATION_RANGES = {
        'smooth_period':   (3, 25),
        'entry_threshold': (0.03, 0.40),
        'ema_period':      (20, 200),
        'atr_period':      (7, 21),
        'sl_atr_mult':     (1.0, 3.0),
        'atr_trail_mult':  (2.0, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        smooth_period: int = 13,
        entry_threshold: float = 0.3529,
        ema_period: int = 179,
        atr_period: int = 9,
        sl_atr_mult: float = 1.9388,
        atr_trail_mult: float = 3.5561,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.smooth_period   = int(smooth_period)
        self.entry_threshold = float(entry_threshold)
        self.ema_period      = int(ema_period)
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
        open_ = df['Open'].astype(float)
        high  = df['High'].astype(float)
        low   = df['Low'].astype(float)

        hl_range = (high - low).clip(lower=1e-8)
        bar_eff  = (close - open_) / hl_range

        smooth = bar_eff.rolling(self.smooth_period).mean()
        ema    = close.ewm(span=self.ema_period, adjust=False).mean()

        df['bar_eff'] = smooth
        df['ema']     = ema
        df['atr']     = calc_atr(df, self.atr_period)

        thresh = self.entry_threshold
        long_cond  = (smooth >  thresh) & (close > ema)
        short_cond = (smooth < -thresh) & (close < ema)

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
