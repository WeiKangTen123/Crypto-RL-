import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class SupertrendATRMomentumStrategy(BaseStrategy):
    """
    Supertrend ATR Momentum Strategy
    ===============================
    Logic:
    1. Enter when Supertrend flips direction and ADX indicates a strong trend.
    2. Exit on Supertrend reversal or ATR-based TP/SL.
    """

    SIGNAL_PARAMS = frozenset({
        'st_period',
        'st_multiplier',
        'adx_period',
        'adx_threshold',
        'atr_period',
        'tp_atr_mult',
        'sl_atr_mult'
    })

    def __init__(
        self,
        df: pd.DataFrame,
        st_period: int = 30,
        st_multiplier: float = 1.8619,
        adx_period: int = 9,
        adx_threshold: float = 27.5287,
        atr_period: int = 6,
        tp_atr_mult: float = 3.9746,
        sl_atr_mult: float = 2.5038,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.st_period = st_period
        self.st_multiplier = st_multiplier
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        
        self._s = {
            1:  dict(sl_price=None, tp_price=None),
            -1: dict(sl_price=None, tp_price=None),
        }

    def _calculate_supertrend(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        hl2 = (df['High'] + df['Low']) / 2
        atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.st_period)
        
        upper_band = hl2 + (self.st_multiplier * atr)
        lower_band = hl2 - (self.st_multiplier * atr)
        
        final_ub = upper_band.copy()
        final_lb = lower_band.copy()
        supertrend = np.zeros(len(df))
        direction = np.zeros(len(df)) # 1 for Long, -1 for Short
        
        # Initialize
        final_ub.iloc[0] = upper_band.iloc[0]
        final_lb.iloc[0] = lower_band.iloc[0]
        
        close = df['Close'].values
        final_ub_val = final_ub.values
        final_lb_val = final_lb.values
        upper_band_val = upper_band.values
        lower_band_val = lower_band.values
        
        for i in range(1, len(df)):
            # Upper Band
            if np.isnan(final_ub_val[i-1]):
                final_ub_val[i] = upper_band_val[i]
            elif (upper_band_val[i] < final_ub_val[i-1]) or (close[i-1] > final_ub_val[i-1]):
                final_ub_val[i] = upper_band_val[i]
            else:
                final_ub_val[i] = final_ub_val[i-1]
                
            # Lower Band
            if np.isnan(final_lb_val[i-1]):
                final_lb_val[i] = lower_band_val[i]
            elif (lower_band_val[i] > final_lb_val[i-1]) or (close[i-1] < final_lb_val[i-1]):
                final_lb_val[i] = lower_band_val[i]
            else:
                final_lb_val[i] = final_lb_val[i-1]
                
            # Direction
            if direction[i-1] == 1:
                if close[i] < final_lb_val[i]:
                    direction[i] = -1
                    supertrend[i] = final_ub_val[i]
                else:
                    direction[i] = 1
                    supertrend[i] = final_lb_val[i]
            elif direction[i-1] == -1:
                if close[i] > final_ub_val[i]:
                    direction[i] = 1
                    supertrend[i] = final_lb_val[i]
                else:
                    direction[i] = -1
                    supertrend[i] = final_ub_val[i]
            else:
                if close[i] > final_ub_val[i]:
                    direction[i] = 1
                    supertrend[i] = final_lb_val[i]
                else:
                    direction[i] = -1
                    supertrend[i] = final_ub_val[i]
                    
        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Indicators
        df['st_val'], df['st_dir'] = self._calculate_supertrend(df)
        df['adx'] = talib.ADX(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=self.adx_period)
        df['atr'] = talib.ATR(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=self.atr_period)
        
        # 2. Signals
        df['st_flip'] = df['st_dir'].diff()
        
        long_cond = (df['st_flip'] == 2) & (df['adx'] > self.adx_threshold)
        short_cond = (df['st_flip'] == -2) & (df['adx'] > self.adx_threshold)
        
        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1
        signals[short_cond] = -1
        
        df['signal'] = signals
        print(f"  [DEBUG] Signals generated: Long={long_cond.sum()}, Short={short_cond.sum()}")
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
        
        # Initialize SL/TP on entry
        if entry_price != getattr(self, f'_last_entry_price_{side}', None):
            setattr(self, f'_last_entry_price_{side}', entry_price)
            atr = row['atr']
            if np.isnan(atr): atr = entry_price * 0.01
            s['sl_price'] = entry_price - side * (atr * self.sl_atr_mult)
            s['tp_price'] = entry_price + side * (atr * self.tp_atr_mult)

        # SL/TP Checks
        price_low = float(row['Low'])
        price_high = float(row['High'])
        price_close = float(row['Close'])
        
        if side == 1:
            if price_low  <= s['sl_price']: return 'SL', s['sl_price']
            if price_high >= s['tp_price']: return 'TP', s['tp_price']
            if price_close < row['st_val']: return 'EXIT', price_close
        else:
            if price_high >= s['sl_price']: return 'SL', s['sl_price']
            if price_low  <= s['tp_price']: return 'TP', s['tp_price']
            if price_close > row['st_val']: return 'EXIT', price_close

        return 'HOLD', None
