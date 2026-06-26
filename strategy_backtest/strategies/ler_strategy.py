import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_bollinger_bands, calc_depth_imbalance, calc_atr, calc_ema

class LERStrategy(BaseStrategy):
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})
    
    SIGNAL_PARAMS = frozenset({
        'bb_period', 'bb_std', 'depth_lookback', 'depth_perc_long', 'depth_perc_short', 'use_depth_filter',
        'tp_multiplier', 'sl_multiplier'
    })

    OPTIMIZATION_RANGES = {
        'bb_period': (10, 30),
        'bb_std': (1.5, 3.0),
        'depth_lookback': (50, 150),
        'use_depth_filter': [True, False],
        'tp_multiplier': (1.0, 4.0),
        'sl_multiplier': (1.0, 3.0),
    }

    def __init__(self, df: pd.DataFrame, 
                 bb_period: int = 27,
                 bb_std: float = 2.3042,
                 depth_lookback: int = 135,
                 depth_perc_long: float = 0.1,
                 depth_perc_short: float = 0.9,
                 use_depth_filter: bool = True,
                 tp_multiplier: float = 3.9506,
                 sl_multiplier: float = 2.3876,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.bb_period = int(bb_period)
        self.bb_std = float(bb_std)
        self.depth_lookback = int(depth_lookback)
        self.depth_perc_long = float(depth_perc_long)
        self.depth_perc_short = float(depth_perc_short)
        self.use_depth_filter = bool(use_depth_filter)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        upper_bb, _, lower_bb = calc_bollinger_bands(df, period=self.bb_period, std=self.bb_std)
        df['upper_bb'] = upper_bb
        df['lower_bb'] = lower_bb
        df['depth_imb'] = calc_depth_imbalance(df, level=1.0)
        df['atr'] = calc_atr(df, 14)
        df['ema_200'] = calc_ema(df, 200)

        df['depth_perc'] = df['depth_imb'].rolling(window=self.depth_lookback).rank(pct=True)

        long_cond = df['Low'] <= df['lower_bb']
        short_cond = df['High'] >= df['upper_bb']

        if self.use_depth_filter:
            long_cond &= (df['depth_perc'] < self.depth_perc_long)
            short_cond &= (df['depth_perc'] > self.depth_perc_short)

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
