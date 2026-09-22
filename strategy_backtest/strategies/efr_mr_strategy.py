import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_zscore, calc_spot_obi, calc_atr, calc_ema

class EFRMRStrategy(BaseStrategy):
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})
    
    SIGNAL_PARAMS = frozenset({
        'fr_zscore_period', 'fr_zscore_thresh', 'spot_obi_thresh', 'use_obi_filter',
        'tp_multiplier', 'sl_multiplier'
    })

    OPTIMIZATION_RANGES = {
        'fr_zscore_period': (40, 100),
        'fr_zscore_thresh': (1.5, 3.0),
        'spot_obi_thresh': (0.1, 0.5),
        'use_obi_filter': [True, False],
        'tp_multiplier': (2.0, 5.0),
        'sl_multiplier': (1.0, 3.0),
    }

    def __init__(self, df: pd.DataFrame, 
                 fr_zscore_period: int = 95,
                 fr_zscore_thresh: float = 2.3294,
                 spot_obi_thresh: float = 0.1553,
                 use_obi_filter: bool = False,
                 tp_multiplier: float = 3.353,
                 sl_multiplier: float = 1.5247,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.fr_zscore_period = int(fr_zscore_period)
        self.fr_zscore_thresh = float(fr_zscore_thresh)
        self.spot_obi_thresh = float(spot_obi_thresh)
        self.use_obi_filter = bool(use_obi_filter)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        df['fr_zscore'] = calc_zscore(df.get('funding_rate', pd.Series(0, index=df.index)), self.fr_zscore_period)
        df['spot_obi'] = calc_spot_obi(df, level=1.0)
        df['atr'] = calc_atr(df, 14)
        df['ema_200'] = calc_ema(df, 200) # regime guard

        long_cond = df['fr_zscore'] < -self.fr_zscore_thresh
        short_cond = df['fr_zscore'] > self.fr_zscore_thresh

        if self.use_obi_filter:
            long_cond &= (df['spot_obi'] > self.spot_obi_thresh)
            short_cond &= (df['spot_obi'] < -self.spot_obi_thresh)

        # Regime Guard
        long_cond &= (df['Close'] > df['ema_200'])
        short_cond &= (df['Close'] < df['ema_200'])

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
