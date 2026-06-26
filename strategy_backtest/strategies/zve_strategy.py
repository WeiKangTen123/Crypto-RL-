import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_keltner_channels,
    calc_zero_lag_macd,
    calc_vwma,
    calc_ema,
    calc_choppiness_index,
    calc_supertrend,
    calc_atr
)

class ZVEStrategy(BaseStrategy):
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    SIGNAL_PARAMS = frozenset({
        'kc_mult', 'chop_thresh',
        'tp_multiplier', 'sl_multiplier'
    })

    OPTIMIZATION_RANGES = {
        'kc_mult': (1.5, 2.5),
        'chop_thresh': (55.0, 65.0),
        'tp_multiplier': (2.0, 6.0),
        'sl_multiplier': (1.0, 3.0),
    }

    def __init__(self, df: pd.DataFrame,
                 kc_mult: float = 2.2159,
                 chop_thresh: float = 57.0941,
                 tp_multiplier: float = 3.1322,
                 sl_multiplier: float = 1.2735,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.kc_mult = float(kc_mult)
        self.chop_thresh = float(chop_thresh)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        df['kc_upper'], df['kc_middle'], df['kc_lower'] = calc_keltner_channels(df, period=20, mult=self.kc_mult)
        df['zmacd_line'], df['zmacd_signal'] = calc_zero_lag_macd(df)
        df['vwma'] = calc_vwma(df, period=20)
        df['ema'] = calc_ema(df, period=20)
        df['chop'] = calc_choppiness_index(df, period=14)
        df['atr'] = calc_atr(df, 14)

        df['chop_high'] = df['chop'].rolling(10).max() > self.chop_thresh
        df['chop_dropping'] = df['chop'] < 50

        long_cond = (df['Close'] > df['kc_upper']) & \
                    (df['zmacd_line'] > df['zmacd_signal']) & \
                    (df['vwma'] > df['ema']) & \
                    df['chop_high'] & df['chop_dropping']

        short_cond = (df['Close'] < df['kc_lower']) & \
                     (df['zmacd_line'] < df['zmacd_signal']) & \
                     (df['vwma'] < df['ema']) & \
                     df['chop_high'] & df['chop_dropping']

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
