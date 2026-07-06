import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_linear_regression_slope, calc_spot_obi, calc_atr, calc_ema

class FRDSStrategy(BaseStrategy):
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})
    
    SIGNAL_PARAMS = frozenset({
        'trend_period', 'use_spot_obi', 'use_regime_filter',
        'tp_multiplier', 'sl_multiplier'
    })

    OPTIMIZATION_RANGES = {
        'trend_period': (8, 24),
        'use_spot_obi': [True, False],
        'use_regime_filter': [True, False],
        'tp_multiplier': (2.0, 6.0),
        'sl_multiplier': (1.0, 3.0),
    }

    def __init__(self, df: pd.DataFrame, 
                 trend_period: int = 23,
                 use_spot_obi: bool = False,
                 use_regime_filter: bool = True,
                 tp_multiplier: float = 7.057,
                 sl_multiplier: float = 2.1989,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.trend_period = int(trend_period)
        self.use_spot_obi = bool(use_spot_obi)
        self.use_regime_filter = bool(use_regime_filter)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        df['price_trend'] = calc_linear_regression_slope(df['Close'], period=self.trend_period)
        df['fr_trend'] = calc_linear_regression_slope(df.get('funding_rate', pd.Series(0, index=df.index)), period=self.trend_period)
        df['spot_obi'] = calc_spot_obi(df, level=1.0)
        df['atr'] = calc_atr(df, 14)
        df['ema_200'] = calc_ema(df, 200)

        # Long Squeeze (Short Entry)
        short_cond = (df['price_trend'] < 0) & (df['fr_trend'] > 0)
        # Short Squeeze (Long Entry)
        long_cond = (df['price_trend'] > 0) & (df['fr_trend'] < 0)

        if self.use_spot_obi:
            short_cond &= (df['spot_obi'] < 0)
            long_cond &= (df['spot_obi'] > 0)

        if self.use_regime_filter:
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
