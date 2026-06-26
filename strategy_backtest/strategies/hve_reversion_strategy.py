import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_donchian_channels,
    calc_vrsi,
    detect_candle_hammer,
    calc_zscore
)

class HVEStrategy(BaseStrategy):
    """
    Hammer Volume Exhaustion Reversion (HVE)
    """

    OPTIMIZATION_RANGES = {
        "dc_period": (10, 30),
        "vrsi_period": (10, 20),
        "vrsi_thresh": (15.0, 35.0),
        "vol_z_thresh": (1.0, 3.0),
        "vol_z_period": (10, 30),
        "use_vol_exhaustion_filter": [True, False],
        "use_hammer_filter": [True, False],
    }

    SIGNAL_PARAMS = frozenset({"dc_period", "vrsi_period", "vrsi_thresh", "vol_z_thresh", "vol_z_period", "use_vol_exhaustion_filter", "use_hammer_filter"})

    def __init__(self, df, **kwargs):
        self.use_vol_exhaustion_filter = kwargs.get('use_vol_exhaustion_filter', True)
        self.use_hammer_filter = kwargs.get('use_hammer_filter', True)
        self.dc_period = 20
        self.vrsi_period = 14
        self.vrsi_thresh = 25.0
        self.vol_z_thresh = 2.0
        self.vol_z_period = 20
        super().__init__(df, **kwargs)
        self._s = {'entry_price': 0.0, 'sl_price': 0.0}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        upper_dc, mid_dc, lower_dc = calc_donchian_channels(df, period=self.dc_period)
        vrsi = calc_vrsi(df, period=self.vrsi_period)
        hammer = detect_candle_hammer(df)
        vol_z = calc_zscore(df['Volume'], period=self.vol_z_period)

        interact_dc = df['Low'] <= lower_dc
        vol_exhaustion = vrsi < self.vrsi_thresh
        vol_ok = vol_exhaustion if self.use_vol_exhaustion_filter else True
        hammer_recent = hammer | hammer.shift(1)
        hammer_ok = hammer_recent if self.use_hammer_filter else True

        df['signal'] = 0
        # Removed the strict vol_z > 2.0 (Volume Spike) requirement to increase trade frequency
        long_cond = interact_dc & vol_ok & hammer_ok
        df.loc[long_cond, 'signal'] = 1
        
        self.mid_dc = mid_dc
        self.df = df
        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position > 0:
            if self._s['entry_price'] != entry_price:
                self._s['entry_price'] = entry_price
                self._s['sl_price'] = row['Low'] * 0.99

            dynamic_tp = self.mid_dc.loc[row.name]
            sl = self._s['sl_price']
            if row['Low']  <= sl:         return 'SL', sl
            if row['High'] >= dynamic_tp: return 'EXIT', None

        return 'HOLD', None
