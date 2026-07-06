import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr


class VolumeCapitulationReversalStrategy(BaseStrategy):
    """
    Volume Capitulation Reversal — adapted from WorldQuant Alpha#43.

    Alpha#43: ts_rank(volume / adv20, 20) * ts_rank(-delta(close, 7), 8)

    Identifies capitulation events: unusual volume during sustained price decline.
    The product of volume-rank × price-decline-rank peaks during panic selling
    (high volume + recent drop) → contrarian buy signal.

    Long entry:  vol_rank × decline_rank > threshold  (volume spike + price drop)
    Short entry: vol_rank × rise_rank   > threshold   (volume spike + price rise)

    Both factors are rolling percentile ranks (0-1). Threshold ~0.35 means both
    factors must simultaneously be in roughly the top 60th percentile.

    Source: WorldQuant 101 Formulaic Alphas — Alpha#43 (Kakushadze 2015)
    """

    SIGNAL_PARAMS = frozenset([
        'adv_period', 'rank_v_period', 'momentum_period', 'rank_m_period', 'signal_threshold'
    ])

    OPTIMIZATION_RANGES = {
        'adv_period':       (10, 40),
        'rank_v_period':    (10, 40),
        'momentum_period':  (3, 15),
        'rank_m_period':    (5, 20),
        'signal_threshold': (0.15, 0.55),
        'atr_period':       (7, 21),
        'sl_atr_mult':      (1.0, 3.0),
        'atr_trail_mult':   (2.0, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        adv_period: int = 21,
        rank_v_period: int = 39,
        momentum_period: int = 12,
        rank_m_period: int = 14,
        signal_threshold: float = 0.2124,
        atr_period: int = 9,
        sl_atr_mult: float = 1.1162,
        atr_trail_mult: float = 4.5985,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.adv_period       = int(adv_period)
        self.rank_v_period    = int(rank_v_period)
        self.momentum_period  = int(momentum_period)
        self.rank_m_period    = int(rank_m_period)
        self.signal_threshold = float(signal_threshold)
        self.atr_period       = int(atr_period)
        self.sl_atr_mult      = float(sl_atr_mult)
        self.atr_trail_mult   = float(atr_trail_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df     = self.df.copy()
        close  = df['Close'].astype(float)
        volume = df['Volume'].astype(float)

        adv      = volume.rolling(self.adv_period).mean()
        rel_vol  = volume / adv.replace(0, np.nan)
        vol_rank = rel_vol.rolling(self.rank_v_period).rank(pct=True)

        price_change  = close.diff(self.momentum_period)
        decline_rank  = (-price_change).rolling(self.rank_m_period).rank(pct=True)
        rise_rank     = price_change.rolling(self.rank_m_period).rank(pct=True)

        buy_signal  = vol_rank * decline_rank
        sell_signal = vol_rank * rise_rank

        thresh = self.signal_threshold

        df['buy_signal']  = buy_signal
        df['sell_signal'] = sell_signal
        df['atr']         = calc_atr(df, self.atr_period)

        df['signal'] = 0
        long_cond  = (buy_signal  > thresh) & (buy_signal  > sell_signal)
        short_cond = (sell_signal > thresh) & (sell_signal >= buy_signal)
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
