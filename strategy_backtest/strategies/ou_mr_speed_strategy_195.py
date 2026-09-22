"""
Strategy 195: OU Mean-Reversion Speed
"""

from typing import Optional, Tuple
import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_ou_mr_speed, calc_ema, calc_atr

class OuMrSpeedStrategy195(BaseStrategy):
    SIGNAL_PARAMS: frozenset = frozenset({'period', 'atr_period', 'tp_mult', 'sl_mult', 'kappa_thresh'})
    OPTIMIZATION_RANGES = {
        'period':        (10,  60),
        'atr_period':    (5,   30),
        'tp_mult':       (1.0, 6.0),
        'sl_mult':       (0.5, 3.0),
        # kappa is annualised × 252; on 1H data most bars exceed 5.0 — need a
        # much higher threshold to select genuinely fast-reverting regimes
        'kappa_thresh':  (20.0, 250.0),
    }

    def __init__(self, df: pd.DataFrame, 
                 period: int = 49, 
                 atr_period: int = 11,
                 tp_mult: float = 5.8046,
                 sl_mult: float = 2.8753,
                 kappa_thresh: float = 219.3001,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.period = period
        self.atr_period = atr_period
        self.tp_mult = tp_mult
        self.sl_mult = sl_mult
        self.kappa_thresh = kappa_thresh

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        # Indicators
        df['kappa'] = calc_ou_mr_speed(df, self.period)
        df['ema_20'] = calc_ema(df, self.period)
        df['atr'] = calc_atr(df, self.atr_period)

        # Entry signals
        df['signal'] = 0
        df.loc[(df['kappa'] > self.kappa_thresh) & (df['Close'] < df['ema_20']), 'signal'] = 1
        df.loc[(df['kappa'] > self.kappa_thresh) & (df['Close'] > df['ema_20']), 'signal'] = -1
        
        self.df = df
        return self.df

    def manage_trade(self, row, position, entry_price, wallet=0):
        atr = row['atr']
        if position > 0:
            if row['Low'] <= entry_price - self.sl_mult * atr: return 'SL', entry_price - self.sl_mult * atr
            if row['High'] >= entry_price + self.tp_mult * atr: return 'TP', entry_price + self.tp_mult * atr
        elif position < 0:
            if row['High'] >= entry_price + self.sl_mult * atr: return 'SL', entry_price + self.sl_mult * atr
            if row['Low'] <= entry_price - self.tp_mult * atr: return 'TP', entry_price - self.tp_mult * atr
        return 'HOLD', None
