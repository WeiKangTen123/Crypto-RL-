"""
Adaptive Volatility-Scaled Oscillator (AVSO) Momentum Strategy
==============================================================================
Category: Trend Following / Momentum
Logic:
1. Calculate raw momentum (Close - Close[n]).
2. Calculate volatility scaling factor (Current ATR / Average ATR).
3. Scale momentum by volatility factor.
4. Signal: Scaled momentum crosses Zero, filtered by volatility threshold.
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class AVSOMomentumStrategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset({
        'length',           # Momentum length
        'smoothing',        # EMA smoothing for AVSO
        'vol_lookback',     # Lookback for average ATR
        'vol_threshold',    # Min volatility scaling to allow entries
        'atr_multiplier_sl',# ATR multiplier for trailing stop
    })

    def __init__(
        self,
        df: pd.DataFrame,
        length: int = 8,
        smoothing: int = 25,
        vol_lookback: int = 44,
        vol_threshold: float = 0.9888,
        atr_multiplier_sl: float = 2.9186,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.length = length
        self.smoothing = smoothing
        self.vol_lookback = vol_lookback
        self.vol_threshold = vol_threshold
        self.atr_multiplier_sl = atr_multiplier_sl
        
        self._s = {
            1:  dict(sl_price=None, trailing_sl=True),
            -1: dict(sl_price=None, trailing_sl=True),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = pd.to_numeric(df['Close'], errors='coerce')
        high = pd.to_numeric(df['High'], errors='coerce')
        low = pd.to_numeric(df['Low'], errors='coerce')
        
        # 1. Momentum
        mom = close.diff(self.length)
        
        # 2. Volatility Factor
        atr = ta.volatility.AverageTrueRange(high, low, close, window=self.length).average_true_range()
        avg_atr = atr.rolling(window=self.vol_lookback).mean()
        vol_factor = (atr / avg_atr).fillna(1.0)
        
        # 3. AVSO
        avso_raw = mom * vol_factor
        avso = avso_raw.ewm(span=self.smoothing, adjust=False).mean()
        
        # 4. Signals
        signals = np.zeros(len(df), dtype=int)
        
        # Crosses above zero
        bullish_cross = (avso > 0) & (avso.shift(1) <= 0)
        # Crosses below zero
        bearish_cross = (avso < 0) & (avso.shift(1) >= 0)
        
        # Volatility Filter
        vol_ok = vol_factor >= self.vol_threshold
        
        signals[bullish_cross & vol_ok] = 1
        signals[bearish_cross & vol_ok] = -1
        
        df['signal'] = signals
        df['atr'] = atr
        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0.0,
    ) -> Tuple[str, Optional[float]]:
        
        if position == 0:
            return 'HOLD', None
            
        side = int(np.sign(position))
        s = self._s[side]
        
        atr = float(row['atr'])
        if np.isnan(atr): atr = entry_price * 0.01
        
        if entry_price != getattr(self, f'_last_entry_price_{side}', None):
            setattr(self, f'_last_entry_price_{side}', entry_price)
            s['sl_price'] = entry_price - side * (atr * self.atr_multiplier_sl)

        # Trailing Stop Logic
        price_low = float(row['Low'])
        price_high = float(row['High'])
        
        if side == 1:
            # Update trailing SL if price makes a new high
            new_sl = price_high - (atr * self.atr_multiplier_sl)
            if new_sl > s['sl_price']:
                s['sl_price'] = new_sl
            
            if price_low <= s['sl_price']:
                return 'SL', s['sl_price']
        else:
            # Update trailing SL if price makes a new low
            new_sl = price_low + (atr * self.atr_multiplier_sl)
            if new_sl < s['sl_price']:
                s['sl_price'] = new_sl
                
            if price_high >= s['sl_price']:
                return 'SL', s['sl_price']

        return 'HOLD', None
