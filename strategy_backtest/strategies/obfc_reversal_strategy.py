import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    detect_order_blocks,
    calc_fisher_transform,
    calc_ema,
    calc_atr,
    detect_fvg,
    window_any_true
)

class OBFCStrategy(BaseStrategy):
    """
    Institutional Order Block Mitigation with Fisher Confirmation (OBFC)
    """

    OPTIMIZATION_RANGES = {
        "ob_lookback": (2, 5),
        "fisher_period": (8, 15),
        "ema_period": (100, 300),
        "atr_period": (10, 20),
        "tp_atr_mult": (2.0, 5.0),
        "sl_atr_mult": (1.0, 3.0),
        "use_ema_filter": [True, False],
        "use_fisher_filter": [True, False],
    }

    SIGNAL_PARAMS = frozenset({"ob_lookback", "fisher_period", "ema_period", "atr_period", "use_ema_filter", "use_fisher_filter"})

    def __init__(self, df, **kwargs):
        self.use_ema_filter = kwargs.get('use_ema_filter', True)
        self.use_fisher_filter = kwargs.get('use_fisher_filter', True)
        self.ob_lookback = 3
        self.fisher_period = 10
        self.ema_period = 200
        self.atr_period = 14
        self.tp_atr_mult = 3.0
        self.sl_atr_mult = 1.0
        super().__init__(df, **kwargs)
        self._s = {'entry_price': 0.0, 'tp_price': 0.0, 'sl_price': 0.0}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        ob_signals = detect_order_blocks(df, atr_period=self.atr_period, atr_multiplier=2.0, ob_lookback=self.ob_lookback)
        fisher, trigger = calc_fisher_transform(df, period=self.fisher_period)
        ema = calc_ema(df, period=self.ema_period)
        atr = calc_atr(df, period=self.atr_period)
        bullish_fvg, _ = detect_fvg(df)

        ema_sloping_up = ema > ema.shift(1)
        ema_ok = ema_sloping_up if self.use_ema_filter else True
        
        # OB touch happened recently (Relaxed window from 3 to 8 bars)
        recent_ob_touch = window_any_true(ob_signals == 1, window=8)
        
        fisher_cross_up = (fisher > trigger) & (fisher.shift(1) <= trigger.shift(1))
        fisher_ok = fisher_cross_up if self.use_fisher_filter else True

        df['signal'] = 0
        # Removed FVG requirement to significantly increase trade frequency
        long_cond = ema_ok & recent_ob_touch & fisher_ok
        df.loc[long_cond, 'signal'] = 1
        
        self.atr_series = atr
        self.df = df
        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position > 0:
            if self._s['entry_price'] != entry_price:
                self._s['entry_price'] = entry_price
                current_atr = self.atr_series.loc[row.name]
                self._s['sl_price'] = entry_price - (current_atr * self.sl_atr_mult)
                self._s['tp_price'] = entry_price + (current_atr * self.tp_atr_mult)

            tp = self._s['tp_price']
            sl = self._s['sl_price']
            if row['Low']  <= sl: return 'SL', sl

            if row['High'] >= tp: return 'TP', tp

        return 'HOLD', None
