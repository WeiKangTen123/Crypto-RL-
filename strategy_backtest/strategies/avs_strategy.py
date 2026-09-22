import pandas as pd
import numpy as np
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_bb_kc_squeeze,
    calc_adx,
    calc_fisher_transform,
    calc_chandelier_exit,
    calc_vrsi,
    window_any_true
)

class AVSStrategy(BaseStrategy):
    """
    Adaptive Volatility Squeeze (AVS) Strategy
    Combines Bollinger/Keltner Squeeze with ADX consolidation regime filtering.
    Uses Fisher Transform for directional breakout trigger, and Chandelier Exit for trailing stops.
    """

    VALID_ACTIONS: frozenset = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP', 'TS'})

    SIGNAL_PARAMS: frozenset = frozenset({
        'bb_period', 'bb_std', 'kc_period', 'kc_mult',
        'adx_period', 'adx_threshold', 'fisher_period',
        'use_vrsi_filter', 'vrsi_period', 'vrsi_threshold',
        'use_regime_filter', 'use_squeeze_filter'
    })

    OPTIMIZATION_RANGES = {
        'adx_threshold': (20, 35),
        'fisher_period': (8, 14),
        'use_vrsi_filter': [True, False],
        'vrsi_threshold': (60, 80),
        'chandelier_mult': (2.0, 4.0),
        'use_regime_filter': [True, False],
        'use_squeeze_filter': [True, False]
    }

    def __init__(self, df: pd.DataFrame,
                 bb_period: int = 43,
                 bb_std: float = 1.8819,
                 kc_period: int = 20,
                 kc_mult: float = 1.5,
                 adx_period: int = 14,
                 adx_threshold: float = 25.0,
                 fisher_period: int = 10,
                 use_vrsi_filter: bool = True,
                 vrsi_period: int = 14,
                 vrsi_threshold: float = 70.0,
                 chandelier_atr_period: int = 22,
                 chandelier_mult: float = 3.0,
                 use_regime_filter: bool = True,
                 use_squeeze_filter: bool = True,
                 **kwargs):
        super().__init__(df, **kwargs)
        # Type-casting inputs explicitly
        self.bb_period = int(bb_period)
        self.bb_std = float(bb_std)
        self.kc_period = int(kc_period)
        self.kc_mult = float(kc_mult)
        self.adx_period = int(adx_period)
        self.adx_threshold = float(adx_threshold)
        self.fisher_period = int(fisher_period)
        self.use_vrsi_filter = bool(use_vrsi_filter)
        self.vrsi_period = int(vrsi_period)
        self.vrsi_threshold = float(vrsi_threshold)
        self.chandelier_atr_period = int(chandelier_atr_period)
        self.chandelier_mult = float(chandelier_mult)
        self.use_regime_filter = bool(use_regime_filter)
        self.use_squeeze_filter = bool(use_squeeze_filter)

        # State dict for exit tracking
        self._s = {
            1:  dict(entry_price=None, ts_price=None),
            -1: dict(entry_price=None, ts_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        df['squeeze'] = calc_bb_kc_squeeze(df, self.bb_period, self.bb_std, self.kc_period, self.kc_mult)
        df['adx'] = calc_adx(df, self.adx_period)
        
        fisher, fisher_trigger = calc_fisher_transform(df, self.fisher_period)
        df['fisher'] = fisher
        df['fisher_trigger'] = fisher_trigger
        
        df['vrsi'] = calc_vrsi(df, self.vrsi_period)

        # Chandelier Exit calculated fully in library
        long_exit, short_exit = calc_chandelier_exit(df, self.chandelier_atr_period, self.chandelier_mult, long_only=False)
        df['chandelier_long'] = long_exit
        df['chandelier_short'] = short_exit

        # Squeeze Filter Switch
        if self.use_squeeze_filter:
            recent_squeeze = window_any_true(df['squeeze'], 3)
        else:
            recent_squeeze = pd.Series(True, index=df.index)
        
        # Consolidation regime filter Switch
        if self.use_regime_filter:
            regime_consolidation = df['adx'] < self.adx_threshold
        else:
            regime_consolidation = pd.Series(True, index=df.index)
        
        # Fisher crossover triggers for breakout direction
        fisher_cross_up = (df['fisher'] > df['fisher_trigger']) & (df['fisher'].shift(1) <= df['fisher_trigger'].shift(1))
        fisher_cross_down = (df['fisher'] < df['fisher_trigger']) & (df['fisher'].shift(1) >= df['fisher_trigger'].shift(1))

        # Basic signal conditions
        long_condition = recent_squeeze & regime_consolidation & fisher_cross_up
        short_condition = recent_squeeze & regime_consolidation & fisher_cross_down
        
        df['signal'] = 0
        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1
        
        # VRSI Volume Exhaustion Filter Switch
        if self.use_vrsi_filter:
            df.loc[(df['signal'] == 1) & (df['vrsi'] > self.vrsi_threshold), 'signal'] = 0
            df.loc[(df['signal'] == -1) & (df['vrsi'] < (100 - self.vrsi_threshold)), 'signal'] = 0
            
        self.df = df
        return self.df

    def manage_trade(self, row: pd.Series, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None
            
        side = int(np.sign(position))
        s = self._s[side]

        # Reset state on new trade (entry_price changed)
        if s['entry_price'] != entry_price:
            s['entry_price'] = entry_price
            initial_stop = row['chandelier_long'] if side == 1 else row['chandelier_short']
            if np.isnan(initial_stop):
                initial_stop = entry_price * (0.95 if side == 1 else 1.05)
            s['ts_price'] = initial_stop

        if side == 1:
            current_stop = row['chandelier_long']
            if not np.isnan(current_stop):
                s['ts_price'] = max(s['ts_price'] if s['ts_price'] is not None else -np.inf, current_stop)
                
            if s['ts_price'] is not None and not np.isnan(s['ts_price']) and row['Low'] <= s['ts_price']:
                return 'TS', s['ts_price']
                
        elif side == -1:
            current_stop = row['chandelier_short']
            if not np.isnan(current_stop):
                s['ts_price'] = min(s['ts_price'] if s['ts_price'] is not None else np.inf, current_stop)
                
            if s['ts_price'] is not None and not np.isnan(s['ts_price']) and row['High'] >= s['ts_price']:
                return 'TS', s['ts_price']

        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """Enforce param constraints during optimization."""
        # Ensure periods are valid positive numbers
        for p in ['bb_period', 'kc_period', 'adx_period', 'fisher_period', 'vrsi_period', 'chandelier_atr_period']:
            if p in params and params[p] < 3:
                return False
        return True
