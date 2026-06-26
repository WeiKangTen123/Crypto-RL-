import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_mcginley_dynamic,
    calc_choppiness_index,
    calc_vrsi,
    calc_adx
)

class MDVBStrategy(BaseStrategy):
    """
    McGinley Dynamic Volume Breakout (MDVB)
    """

    OPTIMIZATION_RANGES = {
        "mcg_slow": (30, 80, int),
        "mcg_fast": (10, 30, int),
        "chop_period": (10, 20, int),
        "chop_threshold": (30.0, 45.0, float),
        "vrsi_period": (10, 20, int),
        "adx_period": (10, 20, int),
        "adx_threshold": (15.0, 30.0, float),
        "use_chop_filter": [True, False],
        "use_adx_filter": [True, False],
        "use_vrsi_filter": [True, False],
    }

    SIGNAL_PARAMS = frozenset({"mcg_slow", "mcg_fast", "chop_period", "chop_threshold", "vrsi_period", "adx_period", "adx_threshold", "use_chop_filter", "use_adx_filter", "use_vrsi_filter"})

    def __init__(self, df, **kwargs):
        self.use_chop_filter = kwargs.get('use_chop_filter', True)
        self.use_adx_filter = kwargs.get('use_adx_filter', True)
        self.use_vrsi_filter = kwargs.get('use_vrsi_filter', True)
        # Defaults
        self.mcg_slow = 50
        self.mcg_fast = 20
        self.chop_period = 14
        self.chop_threshold = 38.2
        self.vrsi_period = 14
        self.adx_period = 14
        self.adx_threshold = 20.0
        super().__init__(df, **kwargs)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        mcg_slow = calc_mcginley_dynamic(df, period=self.mcg_slow)
        mcg_fast = calc_mcginley_dynamic(df, period=self.mcg_fast)
        chop = calc_choppiness_index(df, period=self.chop_period)
        vrsi = calc_vrsi(df, period=self.vrsi_period)
        adx = calc_adx(df, period=self.adx_period)

        # Trend Filter
        trend_up = df['Close'] > mcg_slow
        
        # Choppiness Filter (Relaxed from 38.2 to 50.0 to allow more trades)
        not_choppy = chop < 50.0
        chop_ok = not_choppy if self.use_chop_filter else True

        # ADX Gate
        adx_gate = adx > self.adx_threshold
        adx_ok = adx_gate if self.use_adx_filter else True

        # VRSI Breakout (Relaxed: VRSI is high, rather than a strict 1-bar crossover)
        vrsi_high = vrsi > 50
        vrsi_ok = vrsi_high if self.use_vrsi_filter else True

        # Combine
        df['signal'] = 0
        long_cond = trend_up & chop_ok & adx_ok & vrsi_ok
        df.loc[long_cond, 'signal'] = 1
        
        self.mcg_fast_series = mcg_fast
        self.df = df
        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position > 0:
            current_price = row['Close']
            # We need mcg_fast at current bar
            current_time = row.name
            current_mcg_fast = self.mcg_fast_series.loc[current_time]
            
            if current_price < current_mcg_fast:
                return 'EXIT', None
        return 'HOLD', None
