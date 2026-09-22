"""
Volume-Price Correlation Extremas Strategy
"""
from typing import Optional, Tuple
import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import ts_corr, ts_min, S_log1p, calc_atr

class VolumePriceCorrelationExtremasStrategy(BaseStrategy):
    VALID_ACTIONS: frozenset = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    OPTIMIZATION_RANGES = {
        'window_1':        (5,  35),
        'window_2':        (5,  30),
        'alpha_threshold': (0.1, 0.9),
        'atr_period':      (7,  21),
        'tp_multiplier':   (1.0, 6.0),
        'sl_multiplier':   (0.5, 3.0),
        'mode':            ['momentum', 'reversion'],
    }

    SIGNAL_PARAMS: frozenset = frozenset({
        'window_1',
        'window_2',
        'alpha_threshold',
        'mode', # 'momentum' or 'reversion'
        'atr_period',
        'tp_multiplier',
        'sl_multiplier',
    })

    def __init__(self, df: pd.DataFrame, 
                 window_1: int = 25,
                 window_2: int = 30,
                 alpha_threshold: float = 0.5047,
                 mode: str = 'reversion',
                 atr_period: int = 20,
                 tp_multiplier: float = 5.9141,
                 sl_multiplier: float = 2.8397,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.df = df
        self.window_1 = window_1
        self.window_2 = window_2
        self.alpha_threshold = alpha_threshold
        self.mode = mode
        self.atr_period = atr_period
        self.tp_multiplier = tp_multiplier
        self.sl_multiplier = sl_multiplier

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        df['corr'] = ts_corr(df['High'], df['Volume'], self.window_1)
        df['min_corr'] = ts_min(df['corr'], self.window_2)
        df['alpha'] = S_log1p(df['min_corr'])
        df['atr'] = calc_atr(df, self.atr_period)

        df['signal'] = 0
        
        if self.mode == 'momentum':
            # Positive correlation extremas: high correlation indicates strong trend + volume
            df.loc[df['alpha'] > self.alpha_threshold, 'signal'] = 1
            df.loc[df['alpha'] < -self.alpha_threshold, 'signal'] = -1
        else: # 'reversion'
            # Negative correlation extremas: capitulation/blow-off tops
            df.loc[df['alpha'] < -self.alpha_threshold, 'signal'] = 1
            df.loc[df['alpha'] > self.alpha_threshold, 'signal'] = -1
            
        self.df = df
        return self.df

    def manage_trade(
        self,
        row: pd.Series,
        position: float,
        entry_price: float,
        _wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        current_atr = row['atr']

        if pd.isna(current_atr) or current_atr == 0:
            return 'HOLD', None

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
