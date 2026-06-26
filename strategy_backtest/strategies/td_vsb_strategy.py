import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_bb_kc_squeeze,
    calc_vwap_zscore,
    calc_taker_intensity,
    calc_chandelier_exit,
    calc_atr
)

class TDVSBStrategy(BaseStrategy):
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    SIGNAL_PARAMS = frozenset({
        'vwap_z_thresh', 'taker_thresh',
        'tp_multiplier', 'sl_multiplier'
    })

    OPTIMIZATION_RANGES = {
        'vwap_z_thresh': (1.0, 2.5),
        'taker_thresh': (0.5, 2.5),
        'tp_multiplier': (2.0, 6.0),
        'sl_multiplier': (1.0, 3.0),
    }

    def __init__(self, df: pd.DataFrame,
                 vwap_z_thresh: float = 1.9801,
                 taker_thresh: float = 1.6166,
                 tp_multiplier: float = 5.9518,
                 sl_multiplier: float = 1.031,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.vwap_z_thresh = float(vwap_z_thresh)
        self.taker_thresh = float(taker_thresh)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        df['squeeze'] = calc_bb_kc_squeeze(df)
        df['vwap_z'], _ = calc_vwap_zscore(df, period=20)
        df['taker_int'], _ = calc_taker_intensity(df, period=24)
        df['atr'] = calc_atr(df, 14)

        # Allow breakout if squeeze happened within last 3 bars
        df['squeeze_recent'] = df['squeeze'].rolling(3).max() > 0

        long_cond = df['squeeze_recent'] & (df['vwap_z'] > self.vwap_z_thresh) & (df['taker_int'] > self.taker_thresh)
        short_cond = df['squeeze_recent'] & (df['vwap_z'] < -self.vwap_z_thresh) & (df['taker_int'] > self.taker_thresh)

        df['signal'] = 0
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1

        self.df = df
        return self.df

    def manage_trade(self, row: pd.Series, position: float, entry_price: float, _wallet: float = 0):
        current_atr = row['atr']

        if position > 0:
            tp = entry_price + (self.tp_multiplier * current_atr)
            sl = entry_price - (self.sl_multiplier * current_atr)
            if row['Low']  <= sl: return 'SL', sl

            if row['High'] >= tp: return 'TP', tp

        elif position < 0:
            tp = entry_price - (self.tp_multiplier * current_atr)
            sl = entry_price + (self.sl_multiplier * current_atr)
            if row['High'] >= sl: return 'SL', sl

            if row['Low']  <= tp: return 'TP', tp

        return 'HOLD', None
