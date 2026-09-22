"""
Envelope Mean Reversion Strategy
================================
Core Hypothesis:
  Crypto markets exhibit strong mean-reverting properties on intraday timeframes (15m, 1h) 
  after sudden, sharp deviations. Using price envelopes (SMA + fixed % deviation) 
  can capture these extremes.

Entry:
  LONG  : Close < SMA * (1 - deviation)
  SHORT : Close > SMA * (1 + deviation)

Exit:
  1. Take Profit : Price returns to SMA
  2. Stop Loss   : Fixed percentage or ATR-based
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class EnvelopeMeanReversionStrategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset(['sma_period', 'deviation_pct', 'use_vol_filter', 'vol_ma_period'])

    def __init__(
        self,
        df: pd.DataFrame,
        sma_period: int = 9,
        deviation_pct: float = 0.0546,
        use_vol_filter: bool = True,
        vol_ma_period: int = 26,
        sl_pct: float = 0.1761,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.sma_period = sma_period
        self.deviation_pct = deviation_pct
        self.use_vol_filter = use_vol_filter
        self.vol_ma_period = vol_ma_period
        self.sl_pct = sl_pct
        
        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        
        df['sma'] = close.rolling(window=self.sma_period).mean()
        df['upper_band'] = df['sma'] * (1 + self.deviation_pct)
        df['lower_band'] = df['sma'] * (1 - self.deviation_pct)
        
        long_ok = close < df['lower_band']
        short_ok = close > df['upper_band']
        
        if self.use_vol_filter:
            df['vol_ma'] = df['Volume'].rolling(window=self.vol_ma_period).mean()
            vol_ok = df['Volume'] > df['vol_ma']
            long_ok = long_ok & vol_ok
            short_ok = short_ok & vol_ok
            
        signals = np.zeros(len(df), dtype=int)
        long_edge = long_ok & ~long_ok.shift(1, fill_value=False)
        short_edge = short_ok & ~short_ok.shift(1, fill_value=False)
        signals[long_edge.values] = 1
        signals[short_edge.values] = -1
        
        df['signal'] = signals
        self._sma_arr = df['sma'].values
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None
            
        side = int(np.sign(position))
        s = self._s[side]
        bar_idx = self._bar_index_map.get(row.name, -1)
        curr = float(row['Close'])
        
        if entry_price != s['entry_price']:
            sl = entry_price * (1.0 - side * self.sl_pct)
            s.update(entry_price=entry_price, sl_price=sl)
            
        sma = float(self._sma_arr[bar_idx]) if bar_idx >= 0 else curr
        if side == 1:
            if float(row['Low']) <= s['sl_price']: return 'SL', s['sl_price']
            if curr >= sma: return 'TP', curr
        elif side == -1:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']
            if curr <= sma: return 'TP', curr
            
        return 'HOLD', None
