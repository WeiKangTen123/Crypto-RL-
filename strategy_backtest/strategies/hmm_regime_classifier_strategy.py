import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_hmm_regime_classifier


class HMMRegimeClassifierStrategy(BaseStrategy):
    """
    HMM Regime Classifier — fits a 3-state Gaussian HMM on (log_return, norm_ATR)
    features to label each bar as Bearish (0), Sideways (1), or Bullish (2).

    Factor Card: factor_library/Trend/20260622_hmm_regime_classifier.md
    Registered IDs: 188 (BTC/4h)

    Logic:
      - Fit GaussianHMM on full dataset; decode regime per bar
      - Long:  regime==2 (Bullish) AND Close > EMA(ema_period)
      - Short: regime==0 (Bearish) AND Close < EMA(ema_period)
      - Exit:  regime flips to opposite direction → market exit
               OR ATR trailing stop ratchet fires
    """

    SIGNAL_PARAMS = frozenset(['n_states', 'ema_period'])

    OPTIMIZATION_RANGES = {
        'ema_period':     (20, 100),
        'atr_period':     (7, 21),
        'sl_atr_mult':    (1.0, 3.0),
        'atr_trail_mult': (1.5, 4.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        n_states: int = 3,
        ema_period: int = 89,
        atr_period: int = 7,
        sl_atr_mult: float = 1.5617,
        atr_trail_mult: float = 3.8031,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.n_states      = int(n_states)
        self.ema_period    = int(ema_period)
        self.atr_period    = int(atr_period)
        self.sl_atr_mult   = float(sl_atr_mult)
        self.atr_trail_mult = float(atr_trail_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        regime = calc_hmm_regime_classifier(df, n_states=self.n_states)
        df['regime'] = regime

        ema = talib.EMA(df['Close'].astype(float), timeperiod=self.ema_period)
        df['ema_filter'] = ema
        df['atr']        = calc_atr(df, self.atr_period)

        bullish = (regime == 2) & (df['Close'] > ema)
        bearish = (regime == 0) & (df['Close'] < ema)

        df['signal'] = 0
        df.loc[bullish, 'signal'] = 1
        df.loc[bearish, 'signal'] = -1

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

        # Regime conflict exit — flip to opposite direction
        current_regime = int(row['regime'])
        if side == 1 and current_regime == 0:
            return 'SL', float(row['Close'])
        if side == -1 and current_regime == 2:
            return 'SL', float(row['Close'])

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
