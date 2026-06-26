import pandas as pd
import numpy as np
import talib
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_ema, calc_atr, calc_bollinger_bands, calc_keltner_channels,
    calc_bb_kc_squeeze, calc_supertrend
)

class InstitutionalMomentumConsolidationBreakoutStrategy(BaseStrategy):
    """
    Institutional Momentum Consolidation Breakout Strategy
    
    Logic:
    1. Institutional Momentum: Fast EMA > Slow EMA.
    2. Consolidation: Bollinger Bands inside Keltner Channels (Squeeze) for N periods.
    3. Breakout: Price breaks above the consolidation high with high volume.
    4. Exit: ATR-based TP and SuperTrend-based Trailing SL.
    """
    
    SIGNAL_PARAMS = frozenset({
        'fast_ema', 'slow_ema', 'bb_period', 'bb_std', 'kc_period', 'kc_mult',
        'min_consolidation', 'vol_ma_period', 'atr_lookback'
    })
    
    OPTIMIZATION_RANGES = {
        'fast_ema': [7, 9, 12, 21, 50],
        'slow_ema': [21, 30, 50, 100, 200],
        'bb_period': [10, 20, 30, 50],
        'bb_std': (1.5, 3.5),
        'kc_period': [10, 20, 30, 50],
        'kc_mult': (1.0, 2.5),
        'min_consolidation': [2, 3, 5, 8],
        'vol_ma_period': [10, 20, 50],
        'vol_mult': (1.0, 2.0),
        'tp_atr_mult': (1.5, 6.0),
        'exit_mode': ['FIXED_RR', 'TRAILING_STOP']
    }

    def __init__(self, df, fast_ema=9, slow_ema=21, bb_period=20, bb_std=2.0,
                 kc_period=20, kc_mult=1.5, min_consolidation=3, vol_ma_period=20,
                 vol_mult=1.2, tp_atr_mult=2.5, exit_mode='TRAILING_STOP', **kwargs):
        super().__init__(df, **kwargs)
        self.fast_ema = int(fast_ema)
        self.slow_ema = int(slow_ema)
        self.bb_period = int(bb_period)
        self.bb_std = float(bb_std)
        self.kc_period = int(kc_period)
        self.kc_mult = float(kc_mult)
        self.min_consolidation = int(min_consolidation)
        self.vol_ma_period = int(vol_ma_period)
        self.vol_mult = float(vol_mult)
        self.tp_atr_mult = float(tp_atr_mult)
        self.exit_mode = exit_mode
        
        # State tracking for trades
        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None, cons_low=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None, cons_high=None),
        }

    def generate_signals(self):
        df = self.df.copy()
        
        # Indicators
        df['ema_fast'] = calc_ema(df, self.fast_ema)
        df['ema_slow'] = calc_ema(df, self.slow_ema)
        df['atr'] = calc_atr(df, 14)
        
        # ATR expanding (momentum impulse)
        df['atr_expanding'] = df['atr'] > df['atr'].rolling(5).mean()
        
        # Squeeze detection
        df['squeeze'] = calc_bb_kc_squeeze(df, self.bb_period, self.bb_std, self.kc_period, self.kc_mult)
        
        # Rolling count of consecutive squeeze bars
        df['squeeze_count'] = df['squeeze'].astype(int).groupby((df['squeeze'] != df['squeeze'].shift()).cumsum()).cumsum()
        df.loc[~df['squeeze'], 'squeeze_count'] = 0
        
        # Consolidation High/Low during squeeze
        df['cons_high'] = df['High'].rolling(window=self.min_consolidation).max()
        df['cons_low'] = df['Low'].rolling(window=self.min_consolidation).min()
        
        # Volume filter
        df['vol_ma'] = df['Volume'].rolling(window=self.vol_ma_period).mean()
        
        # SuperTrend for trailing stop
        df['st'], df['st_dir'] = calc_supertrend(df, period=10, multiplier=3.0)
        
        # Signal Logic
        momentum_long = (df['ema_fast'] > df['ema_slow']) & df['atr_expanding'].shift(self.min_consolidation)
        
        squeeze_qualified = df['squeeze_count'].shift(1) >= self.min_consolidation
        breakout_long = (df['Close'] > df['cons_high'].shift(1)) & (df['Volume'] > df['vol_ma'] * self.vol_mult)
        
        df['signal'] = 0
        df.loc[momentum_long & squeeze_qualified & breakout_long, 'signal'] = 1
        
        self.df = df
        return df

    def manage_trade(self, row, position, entry_price, wallet=0):
        if position == 0:
            return 'HOLD', None
        
        side = int(np.sign(position))
        s = self._s[side]
        atr = float(row['atr'])
        
        # Reset state when a NEW trade starts
        if s['entry_price'] != entry_price:
            # SL: Below the low of the consolidation range
            # We'll use the consolidation low captured at signal time
            # Since we don't have easy access to signal time 'cons_low' in manage_trade without storing it in df,
            # we can look it up or use a default ATR-based SL if cons_low is not ideal.
            # Let's use the row's 'cons_low' from the previous bar (which was the consolidation low)
            sl = float(row['cons_low']) if side == 1 else float(row['cons_high'])
            
            # Sanity check for SL: if it's too close or on wrong side, use ATR
            if side == 1 and (sl >= entry_price or sl < entry_price * 0.9):
                 sl = entry_price - (2.0 * atr)
            if side == -1 and (sl <= entry_price or sl > entry_price * 1.1):
                 sl = entry_price + (2.0 * atr)
                 
            tp = entry_price + side * (self.tp_atr_mult * atr)
            s.update(entry_price=entry_price, sl_price=sl, tp_price=tp, ts_price=sl)

        st_val = float(row['st'])
        st_dir = float(row['st_dir'])

        if side == 1:
            if self.exit_mode == 'FIXED_RR':
                if row['Low']  <= s['sl_price']: return 'SL', s['sl_price']

                if row['High'] >= s['tp_price']: return 'TP', s['tp_price']
            else:
                if row['Low'] <= s['sl_price']: return 'SL', s['sl_price']
                if st_dir == 1:
                    s['ts_price'] = max(s['ts_price'] or 0, st_val)
                if row['Low'] <= s['ts_price']: return 'TS', s['ts_price']
        else:
            if self.exit_mode == 'FIXED_RR':
                if row['High'] >= s['sl_price']: return 'SL', s['sl_price']

                if row['Low']  <= s['tp_price']: return 'TP', s['tp_price']
            else:
                if row['High'] >= s['sl_price']: return 'SL', s['sl_price']
                if st_dir == -1:
                    s['ts_price'] = min(s['ts_price'] or 999999, st_val)
                if row['High'] >= s['ts_price']: return 'TS', s['ts_price']

        return 'HOLD', None

    @classmethod
    def validate_params(cls, params):
        if params.get('fast_ema', 0) >= params.get('slow_ema', 1):
            return False
        return True
