import numpy as np
import pandas as pd
from typing import Optional, Tuple
import talib
from strategy_backtest.base_strategy import BaseStrategy

class DumpReversalPeakTrailStrategy(BaseStrategy):
    """
    Dump Reversal Peak Trail (DRPT) Strategy
    ========================================
    Identifies extreme downward price anomalies (dips) that break N-period lows with high volume (dump).
    Waits for a confirmed reversal (green candle or RSI recovery) before entry.
    Exits via Peak-retrace trailing stop or hard SL.
    """

    SIGNAL_PARAMS = frozenset({
        'low_lookback', 'vol_ma_period', 'vol_multiplier', 'rsi_period', 'rsi_threshold',
        'stop_loss_pct', 'peak_retrace_pct'
    })

    def __init__(
        self,
        df: pd.DataFrame,
        low_lookback: int = 288,
        vol_ma_period: int = 20,
        vol_multiplier: float = 2.0,
        rsi_period: int = 14,
        rsi_threshold: float = 30.0,
        stop_loss_pct: float = 0.015,
        peak_retrace_pct: float = 0.02,
        **kwargs
    ):
        super().__init__(
            df,
            low_lookback=low_lookback,
            vol_ma_period=vol_ma_period,
            vol_multiplier=vol_multiplier,
            rsi_period=rsi_period,
            rsi_threshold=rsi_threshold,
            stop_loss_pct=stop_loss_pct,
            peak_retrace_pct=peak_retrace_pct,
            **kwargs
        )
        self._s = {
            1:  dict(entry_price=None, peak_price=0.0, count=0),
            -1: dict(entry_price=None, peak_price=float('inf'), count=0),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Donchian Low (previous bars)
        df['low_channel'] = df['Low'].rolling(window=self.low_lookback).min().shift(1)
        
        # 2. Volume MA
        df['vol_ma'] = df['Volume'].rolling(window=self.vol_ma_period).mean()
        
        # 3. RSI
        # Handle cases where talib might fail or return NaN
        df['rsi'] = talib.RSI(df['Close'].values.astype(float), timeperiod=self.rsi_period)
        
        # 4. Dump Condition
        is_dump = (df['Low'] < df['low_channel']) & (df['Volume'] > df['vol_ma'] * self.vol_multiplier)
        
        # 5. Confirmation
        # Dump must have happened in the last 5 bars
        dump_in_window = is_dump.rolling(window=5, min_periods=1).max().fillna(0).astype(bool)
        
        confirm_green = df['Close'] > df['Open']
        confirm_rsi   = (df['rsi'] > self.rsi_threshold) & (df['rsi'].shift(1) <= self.rsi_threshold)
        
        long_ok = dump_in_window & (confirm_green | confirm_rsi)
        
        # 6. Rising Edge
        long_edge = long_ok & ~long_ok.shift(1).fillna(False)
        
        signals = np.zeros(len(df), dtype=int)
        signals[long_edge.values] = 1
        
        df['signal'] = signals
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
        if side == -1: # Only Long implemented for this specific strategy
            return 'EXIT', None
            
        s = self._s[side]
        if entry_price != s['entry_price']:
            s.update(entry_price=entry_price, peak_price=float(row['High']), count=0)
            
        s['count'] += 1
        s['peak_price'] = max(s['peak_price'], float(row['High']))
        
        # 1. Stop Loss
        sl_price = entry_price * (1.0 - self.stop_loss_pct)
        if float(row['Low']) <= sl_price:
            return 'SL', sl_price
            
        # 2. Peak-retrace trailing stop
        # Only active if we have a peak price higher than entry
        if s['peak_price'] > entry_price:
             trail_price = s['peak_price'] * (1.0 - self.peak_retrace_pct)
             if float(row['Low']) <= trail_price:
                 return 'EXIT', trail_price
                 
        return 'HOLD', None
