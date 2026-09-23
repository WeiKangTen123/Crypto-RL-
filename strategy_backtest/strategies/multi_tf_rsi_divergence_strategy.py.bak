"""
Multi-Timeframe RSI Divergence Strategy
==============================================================================
Category: Reversal / Momentum
Logic:
1. Detect RSI Divergence on 1h timeframe.
2. Filter: Only take 1h signals if 4h timeframe (resampled) shows a similar divergence
   or is in an extreme oversold/overbought state.
"""

import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class MultiTFRSIDivergenceStrategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset({
        'rsi_period',
        'lookback',         # Lookback for pivot comparison
        'pivot_window',     # Bars to confirm a pivot (local low/high)
        'rsi_low',          # RSI oversold threshold
        'rsi_high',         # RSI overbought threshold
        'sl_atr_mult',
        'tp_rr',
    })

    def __init__(
        self,
        df: pd.DataFrame,
        rsi_period: int = 11,
        lookback: int = 10,
        pivot_window: int = 27,
        rsi_low: float = 41.2016,
        rsi_high: float = 79.3183,
        sl_atr_mult: float = 1.6464,
        tp_rr: float = 6.9345,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.rsi_period = rsi_period
        self.lookback = lookback
        self.pivot_window = pivot_window
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.sl_atr_mult = sl_atr_mult
        self.tp_rr = tp_rr
        
        self._s = {
            1:  dict(sl_price=None, tp_price=None),
            -1: dict(sl_price=None, tp_price=None),
        }

    def _detect_divergence(self, df_input, rsi_col='rsi'):
        high = df_input['High'].values
        low = df_input['Low'].values
        rsi = df_input[rsi_col].values
        
        bull_div = np.zeros(len(df_input), dtype=bool)
        bear_div = np.zeros(len(df_input), dtype=bool)
        
        last_low_p, last_low_r = np.nan, np.nan
        last_high_p, last_high_r = np.nan, np.nan
        
        w = self.pivot_window
        for i in range(w, len(df_input) - w):
            # Bullish Pivot (Low)
            if low[i] == np.min(low[i-w:i+w+1]):
                if not np.isnan(last_low_p):
                    if low[i] < last_low_p and rsi[i] > last_low_r and rsi[i] < self.rsi_low:
                        bull_div[i+w] = True # Confirmed at i+w
                last_low_p, last_low_r = low[i], rsi[i]
            
            # Bearish Pivot (High)
            if high[i] == np.max(high[i-w:i+w+1]):
                if not np.isnan(last_high_p):
                    if high[i] > last_high_p and rsi[i] < last_high_r and rsi[i] > self.rsi_high:
                        bear_div[i+w] = True
                last_high_p, last_high_r = high[i], rsi[i]
                
        return bull_div, bear_div

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        for col in ['High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 1. 1h RSI
        df['rsi'] = talib.RSI(df['Close'], timeperiod=self.rsi_period)
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        
        bull_1h, bear_1h = self._detect_divergence(df, 'rsi')
        
        # 2. 4h RSI (Resampled)
        df_4h = df.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        df_4h['rsi_4h'] = talib.RSI(df_4h['Close'], timeperiod=self.rsi_period)
        
        bull_4h_bool, bear_4h_bool = self._detect_divergence(df_4h, 'rsi_4h')
        
        # Realignment
        df_4h['bull_4h'] = bull_4h_bool
        df_4h['bear_4h'] = bear_4h_bool
        
        # We also want to know if 4h RSI is extreme
        df_4h['rsi_4h_low'] = df_4h['rsi_4h'] < self.rsi_low
        df_4h['rsi_4h_high'] = df_4h['rsi_4h'] > self.rsi_high
        
        # Align to 1h
        aligned_4h = df_4h[['bull_4h', 'bear_4h', 'rsi_4h_low', 'rsi_4h_high']].reindex(df.index, method='ffill').fillna(False)
        
        # 3. Signals
        # Entry if 1h Divergence AND (4h Divergence OR 4h Extreme)
        long_ok = bull_1h & (aligned_4h['bull_4h'] | aligned_4h['rsi_4h_low'])
        short_ok = bear_1h & (aligned_4h['bear_4h'] | aligned_4h['rsi_4h_high'])
        
        signals = np.zeros(len(df), dtype=int)
        signals[long_ok] = 1
        signals[short_ok] = -1
        
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
        s = self._s[side]
        
        atr = self.df.at[row.name, 'atr']
        if np.isnan(atr): atr = entry_price * 0.01
        
        if entry_price != getattr(self, f'_last_entry_price_{side}', None):
            setattr(self, f'_last_entry_price_{side}', entry_price)
            s['sl_price'] = entry_price - side * (atr * self.sl_atr_mult)
            s['tp_price'] = entry_price + side * (atr * self.sl_atr_mult * self.tp_rr)

        # SL/TP
        price_low = float(row['Low'])
        price_high = float(row['High'])
        
        if side == 1:
            if price_low  <= s['sl_price']: return 'SL', s['sl_price']
            if price_high >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if price_high >= s['sl_price']: return 'SL', s['sl_price']
            if price_low  <= s['tp_price']: return 'TP', s['tp_price']

        return 'HOLD', None
