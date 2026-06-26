import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_bb_kc_squeeze

class SqueezeMomentumStrategy(BaseStrategy):
    """
    Squeeze Momentum Strategy.
    Enters when Bollinger Bands compress inside Keltner Channels (squeeze), then
    uses an EMA trend filter to determine direction on squeeze release.
    direction='both'      — long and short on squeeze release (EMA-filtered)
    direction='long_only' — only take long entries
    direction='short_only'— only take short entries
    """

    OPTIMIZATION_RANGES = {
        'bb_period':         (10, 30),
        'bb_std':            (1.5, 3.0),
        'kc_period':         (10, 30),
        'kc_mult':           (1.0, 3.0),
        'ema_trend_period':  (20, 100),
        'atr_period':        (7,  21),
        'atr_multiplier_sl': (0.5, 3.0),
        'atr_multiplier_tp': (1.0, 6.0),
        'direction':         ['both', 'long_only', 'short_only'],
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.bb_period         = kwargs.get('bb_period', 20)
        self.bb_std            = kwargs.get('bb_std', 2.0)
        self.kc_period         = kwargs.get('kc_period', 20)
        self.kc_mult           = kwargs.get('kc_mult', 1.5)
        self.ema_trend_period  = kwargs.get('ema_trend_period', 50)
        self.atr_period        = kwargs.get('atr_period', 14)
        self.atr_multiplier_sl = kwargs.get('atr_multiplier_sl', 1.5)
        self.atr_multiplier_tp = kwargs.get('atr_multiplier_tp', 3.0)
        self.direction         = kwargs.get('direction', 'both')

    def generate_signals(self) -> pd.DataFrame:
        squeeze = calc_bb_kc_squeeze(
            self.df,
            bb_period=self.bb_period,
            bb_std=self.bb_std,
            kc_period=self.kc_period,
            kc_mult=self.kc_mult,
        )
        self.df['is_squeeze'] = squeeze

        # Squeeze release: was in squeeze last bar, now not
        squeeze_release = squeeze.astype(int).diff() == -1

        ema = talib.EMA(self.df['Close'], timeperiod=self.ema_trend_period)
        self.df['ema_trend'] = ema
        self.df['atr'] = talib.ATR(
            self.df['High'], self.df['Low'], self.df['Close'],
            timeperiod=self.atr_period
        )

        above_ema = self.df['Close'] > ema
        below_ema = self.df['Close'] < ema

        self.df['signal'] = 0

        if self.direction in ('both', 'long_only'):
            self.df.loc[squeeze_release & above_ema, 'signal'] = 1
        if self.direction in ('both', 'short_only'):
            self.df.loc[squeeze_release & below_ema, 'signal'] = -1

        return self.df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        atr = getattr(row, 'atr', None)
        if atr is None or (isinstance(atr, float) and np.isnan(atr)):
            return 'HOLD', None

        if position > 0:
            tp = entry_price + self.atr_multiplier_tp * atr
            sl = entry_price - self.atr_multiplier_sl * atr
            if float(row['Low'])  <= sl: return 'SL', sl

            if float(row['High']) >= tp: return 'TP', tp
        elif position < 0:
            tp = entry_price - self.atr_multiplier_tp * atr
            sl = entry_price + self.atr_multiplier_sl * atr
            if float(row['High']) >= sl: return 'SL', sl

            if float(row['Low'])  <= tp: return 'TP', tp

        return 'HOLD', None
