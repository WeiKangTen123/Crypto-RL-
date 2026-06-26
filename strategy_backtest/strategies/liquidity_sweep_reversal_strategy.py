"""
Liquidity Sweep & Reversal Strategy
==============================================================================
Detects "stop-hunts" where price sweeps beyond recent swing levels and reverses.
Uses CVD (Cumulative Volume Delta) to confirm institutional absorption.

Logic:
1. Identify Swing High/Low over a lookback period.
2. Bullish Signal: Price breaks below Swing Low but closes back above it.
3. Bearish Signal: Price breaks above Swing High but closes back below it.
4. Filter: CVD exhaustion (CVD not making new extremes during the sweep).
5. Management: ATR-based TP/SL.
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class LiquiditySweepReversalStrategy(BaseStrategy):
    OPTIMIZATION_RANGES = {
        'lookback':          (5,   50),
        'cvd_window':        (5,   50),
        'atr_multiplier_tp': (1.0,  8.0),
        'atr_multiplier_sl': (0.5,  3.0),
        'direction_mode':    ['BOTH', 'LONG_ONLY', 'SHORT_ONLY'],
    }

    SIGNAL_PARAMS = frozenset({'lookback', 'cvd_window', 'direction_mode'})

    def __init__(
        self,
        df: pd.DataFrame,
        lookback: int = 27,
        cvd_window: int = 34,
        atr_multiplier_tp: float = 5.5647,
        atr_multiplier_sl: float = 2.7211,
        direction_mode: str = 'LONG_ONLY',
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.lookback = lookback
        self.cvd_window = cvd_window
        self.atr_multiplier_tp = atr_multiplier_tp
        self.atr_multiplier_sl = atr_multiplier_sl
        self.direction_mode = direction_mode
        
        self._s = {
            1:  dict(entry_price=None, tp_price=None, sl_price=None),
            -1: dict(entry_price=None, tp_price=None, sl_price=None),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Swing High/Low (Donchian Channel style)
        df['swing_high'] = df['High'].shift(1).rolling(window=self.lookback).max()
        df['swing_low'] = df['Low'].shift(1).rolling(window=self.lookback).min()
        
        # 2. CVD (Cumulative Volume Delta)
        taker_buy = pd.to_numeric(df['taker_buy_base_vol'], errors='coerce').fillna(0)
        volume = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
        df['delta'] = 2 * taker_buy - volume
        df['cvd'] = df['delta'].rolling(window=self.cvd_window).sum() 
        
        # 3. Detection
        bullish_sweep = (df['Low'] < df['swing_low']) & (df['Close'] > df['swing_low'])
        bearish_sweep = (df['High'] > df['swing_high']) & (df['Close'] < df['swing_high'])
        
        # 4. CVD Exhaustion Filter
        df['cvd_low'] = df['cvd'].shift(1).rolling(window=self.lookback).min()
        bullish_exhaustion = df['cvd'] > df['cvd_low']
        
        df['cvd_high'] = df['cvd'].shift(1).rolling(window=self.lookback).max()
        bearish_exhaustion = df['cvd'] < df['cvd_high']
        
        # 5. Signals — respect direction mode
        long_ok  = bullish_sweep & bullish_exhaustion
        short_ok = bearish_sweep & bearish_exhaustion

        signals = np.zeros(len(df), dtype=int)
        if self.direction_mode != 'SHORT_ONLY':
            signals[long_ok.values] = 1
        if self.direction_mode != 'LONG_ONLY':
            signals[short_ok.values] = -1
        
        df['signal'] = signals
        
        # Pre-calculate ATR for trade management
        df['atr'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range()
        self._atr_arr = df['atr'].values
        
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0: return 'HOLD', None
        side = int(np.sign(position))
        s = self._s[side]
        bar_idx = self._bar_index_map.get(row.name, -1)
        
        if entry_price != s['entry_price']:
            atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0
            s.update(
                entry_price=entry_price, 
                tp_price=entry_price + side * (self.atr_multiplier_tp * atr),
                sl_price=entry_price - side * (self.atr_multiplier_sl * atr)
            )
        
        if side == 1:
            if row['Low']  <= s['sl_price']: return 'SL', s['sl_price']

            if row['High'] >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if row['High'] >= s['sl_price']: return 'SL', s['sl_price']

            if row['Low']  <= s['tp_price']: return 'TP', s['tp_price']

        return 'HOLD', None
