import pandas as pd
import numpy as np
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_vegas_tunnel,
    calc_vegas_macro_tunnel,
    calc_vegas_distance_zscore,
    calc_vegas_mean_score,
    calc_zscore,
    calc_ema,
    calc_sma,
    calc_atr,
    calc_adx
)

class VegasZScoreStrategy(BaseStrategy):
    """
    Vegas Tunnel + Z-Score Statistical Momentum Strategy.
    
    Combines:
    1. Vegas Tunnel (EMA 144 / 169) as the dynamic trend watershed and structural boundary.
    2. Macro Vegas Tunnel (EMA 576 / 676) for long-term secular regime filtering.
    3. Fast EMA (EMA 12) filter line for momentum breakout confirmation.
    4. Price Z-Score (calc_zscore) ensuring statistical expansion at entry.
    5. Vegas Mean Score (calc_vegas_mean_score) confirming extension above tunnel mean.
    6. Volume surge filter (calc_sma) and ADX trend strength (calc_adx) to eliminate low-liquidity chop.
    7. Structural exit at the opposite Vegas Tunnel band to capture multi-month macro trends.
    """

    SIGNAL_PARAMS = frozenset({
        'p_fast', 'p_slow', 'p_macro', 'p_filter',
        'z_period', 'z_thresh', 'mean_score_thresh',
        'adx_thresh', 'vol_mult', 'sl_atr_mult', 'allow_short'
    })

    OPTIMIZATION_RANGES = {
        'p_fast': (120, 160),
        'p_slow': (150, 190),
        'p_macro': (500, 700),
        'p_filter': (9, 21),
        'z_period': (10, 50),
        'z_thresh': (0.2, 1.2),
        'mean_score_thresh': (0.0, 1.5),
        'adx_thresh': (15.0, 30.0),
        'vol_mult': (0.7, 1.3),
        'sl_atr_mult': (1.5, 4.0),
        'allow_short': [False, True],
    }

    def __init__(self, df: pd.DataFrame,
                 p_fast: int = 144,
                 p_slow: int = 169,
                 p_macro: int = 576,
                 p_filter: int = 12,
                 z_period: int = 20,
                 z_thresh: float = 0.5,
                 mean_score_thresh: float = 0.5,
                 adx_thresh: float = 20.0,
                 vol_mult: float = 0.9,
                 sl_atr_mult: float = 2.5,
                 allow_short: bool = False,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.p_fast = int(p_fast)
        self.p_slow = int(p_slow)
        self.p_macro = int(p_macro)
        self.p_filter = int(p_filter)
        self.z_period = int(z_period)
        self.z_thresh = float(z_thresh)
        self.mean_score_thresh = float(mean_score_thresh)
        self.adx_thresh = float(adx_thresh)
        self.vol_mult = float(vol_mult)
        self.sl_atr_mult = float(sl_atr_mult)
        self.allow_short = bool(allow_short)
        
        # State tracking for position risk management
        self._s = {'entry_price': 0.0, 'sl': 0.0}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. Vegas Primary & Macro Tunnels (Pure Library Factors)
        ema_fast, ema_slow, vegas_mid = calc_vegas_tunnel(df, self.p_fast, self.p_slow)
        ema_macro_f, _, _ = calc_vegas_macro_tunnel(df, self.p_macro, 676)
        ema_filter = calc_ema(df, self.p_filter)

        vegas_top = np.maximum(ema_fast, ema_slow)
        vegas_bot = np.minimum(ema_fast, ema_slow)

        # 2. Statistical Z-Score & Mean Score (Pure Library Factors)
        z_price = calc_zscore(df['Close'], period=self.z_period)
        mean_score = calc_vegas_mean_score(df, self.p_fast, self.p_slow, atr_period=14)

        # 3. Volatility & Trend Strength (Pure Library Factors)
        atr = calc_atr(df, period=14)
        adx = calc_adx(df, period=14)
        vol_sma = calc_sma(df['Volume'], period=20)

        df['vegas_top'] = vegas_top
        df['vegas_bot'] = vegas_bot
        df['atr'] = atr

        # 4. Long Entry Confluence
        # - Price and fast trigger EMA both above Vegas Tunnel
        # - Macro bull regime (Price above Macro EMA 576)
        # - Statistical Z-Score expansion above z_thresh
        # - Normalized Vegas Mean Score above mean_score_thresh
        # - Trend strength confirmation (ADX > adx_thresh)
        # - Institutional Volume confirmation (Volume > vol_mult * SMA)
        long_tunnel = (df['Close'] > vegas_top) & (ema_filter > vegas_top)
        long_macro = df['Close'] > ema_macro_f
        long_mom = (z_price > self.z_thresh) & (mean_score > self.mean_score_thresh)
        long_adx = adx > self.adx_thresh
        long_vol = df['Volume'] > (vol_sma * self.vol_mult)

        long_cond = long_tunnel & long_macro & long_mom & long_adx & long_vol
        long_trigger = long_cond & (~long_cond.shift(1, fill_value=False))

        signal = np.zeros(len(df), dtype=int)
        signal[long_trigger.fillna(False)] = 1

        # 5. Optional Short Entry Confluence
        if self.allow_short:
            short_tunnel = (df['Close'] < vegas_bot) & (ema_filter < vegas_bot)
            short_macro = df['Close'] < ema_macro_f
            short_mom = (z_price < -self.z_thresh) & (mean_score < -self.mean_score_thresh)
            short_cond = short_tunnel & short_macro & short_mom & long_adx & long_vol
            short_trigger = short_cond & (~short_cond.shift(1, fill_value=False))
            signal[short_trigger.fillna(False)] = -1

        df['signal'] = signal
        self.df = df
        return self.df

    def manage_trade(self, row: pd.Series, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        # Detect new trade entry and reset risk bounds
        if entry_price != self._s['entry_price']:
            self._s['entry_price'] = entry_price
            atr = row['atr'] if pd.notna(row['atr']) and row['atr'] > 0 else entry_price * 0.02
            if position > 0:
                self._s['sl'] = entry_price - (self.sl_atr_mult * atr)
            else:
                self._s['sl'] = entry_price + (self.sl_atr_mult * atr)

        if position > 0:
            # 1. Structural Exit: Close falls below the lower band of the Vegas Tunnel
            if row['Close'] < row['vegas_bot']:
                return 'EXIT', row['Close']
            # 2. Hard Stop Loss: Bar low penetrates ATR stop
            if row['Low'] <= self._s['sl']:
                return 'SL', self._s['sl']

        elif position < 0:
            # 1. Structural Exit: Close rallies above the upper band of the Vegas Tunnel
            if row['Close'] > row['vegas_top']:
                return 'EXIT', row['Close']
            # 2. Hard Stop Loss: Bar high penetrates ATR stop
            if row['High'] >= self._s['sl']:
                return 'SL', self._s['sl']

        return 'HOLD', None
