import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr


class FisherExtremeReversalStrategy(BaseStrategy):
    """
    Fisher Transform Extreme Reversal — entry only when Fisher reaches extreme
    spike (< -threshold or > +threshold) AND crosses its EMA signal line.
    TP when Fisher crosses back through zero; SL at ATR multiple.

    Factor Card: factor_library/Mean_Reversion/20260527_fisher_transform_reversal.md
    Registered IDs: 186 (BTC/1h)

    Logic:
      - Long:  Fisher < -extreme_thresh AND Fisher crosses above signal (EMA of Fisher)
      - Short: Fisher > +extreme_thresh AND Fisher crosses below signal
      - TP:    Fisher crosses zero (mean reversion complete)
      - SL:    ATR × sl_atr_mult from entry
    """

    SIGNAL_PARAMS = frozenset(['fisher_period', 'signal_period', 'extreme_thresh'])

    OPTIMIZATION_RANGES = {
        'fisher_period':  (5, 20),
        'signal_period':  (3, 15),
        'extreme_thresh': (1.0, 2.5),
        'atr_period':     (7, 21),
        'sl_atr_mult':    (0.5, 3.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        fisher_period: int = 13,
        signal_period: int = 12,
        extreme_thresh: float = 1.8414,
        atr_period: int = 14,
        sl_atr_mult: float = 0.5034,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.fisher_period  = int(fisher_period)
        self.signal_period  = int(signal_period)
        self.extreme_thresh = float(extreme_thresh)
        self.atr_period     = int(atr_period)
        self.sl_atr_mult    = float(sl_atr_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df   = self.df.copy()
        high = df['High']
        low  = df['Low']
        n    = len(df)

        # Fisher Transform (Ehlers formula — causal smoothed)
        hh = high.rolling(self.fisher_period).max()
        ll = low.rolling(self.fisher_period).min()
        raw = 2.0 * (df['Close'] - ll) / (hh - ll + 1e-10) - 1.0
        raw = raw.clip(-0.999, 0.999)

        value  = np.zeros(n)
        fisher = np.zeros(n)
        for i in range(1, n):
            if np.isnan(raw.iloc[i]):
                continue
            value[i]  = 0.33 * raw.iloc[i] + 0.67 * value[i - 1]
            v          = max(min(value[i], 0.999), -0.999)
            fisher[i]  = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * fisher[i - 1]

        df['fisher'] = fisher
        df['signal'] = talib.EMA(df['fisher'].astype(float), timeperiod=self.signal_period)
        df['atr']    = calc_atr(df, self.atr_period)

        prev_fisher = df['fisher'].shift(1)
        prev_sig    = df['signal'].shift(1)

        # Cross above signal from oversold extreme
        cross_up   = (df['fisher'] > df['signal']) & (prev_fisher <= prev_sig)
        # Cross below signal from overbought extreme
        cross_down = (df['fisher'] < df['signal']) & (prev_fisher >= prev_sig)

        long_cond  = cross_up   & (df['fisher'] < -self.extreme_thresh)
        short_cond = cross_down & (df['fisher'] >  self.extreme_thresh)

        df['signal_col'] = 0
        df.loc[long_cond,  'signal_col'] = 1
        df.loc[short_cond, 'signal_col'] = -1
        df.rename(columns={'signal_col': 'signal', 'signal': 'fisher_sig'}, inplace=True)

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

        sl = s['sl_price']

        if side == 1:
            if float(row['Low']) <= sl:
                return 'SL', sl
            # TP: Fisher crosses back above zero
            if float(row['fisher']) >= 0:
                return 'TP', float(row['Close'])
        else:
            if float(row['High']) >= sl:
                return 'SL', sl
            # TP: Fisher crosses back below zero
            if float(row['fisher']) <= 0:
                return 'TP', float(row['Close'])

        return 'HOLD', None
