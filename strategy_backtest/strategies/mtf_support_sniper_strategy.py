import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class MTFSupportSniperStrategy(BaseStrategy):
    """
    MTF Support Sniper Strategy
    ===========================
    Uses Higher Timeframe (HTF) rolling equivalents on a LTF chart (e.g. 5m)
    to find macro support zones (Daily VWAP, Macro EMA). 
    Uses LTF V-RSI to snipe the exact bottom of the pullback into support.
    """
    OPTIMIZATION_RANGES = {
        'htf_vwap_period': (100, 1500),
        'htf_ema_period': (500, 5000),
        'zone_pct': (0.005, 0.05),         # Wider zone for sweeps
        'vrsi_period': (10, 50),
        'vrsi_oversold': (10.0, 45.0),     # Doesn't need to be as extreme now
        'sl_pct': (0.015, 0.08),           # Wider stop (1.5% to 8%) to survive noise
        'tp_pct': (0.03, 0.25),            # Massive bounce target
        'max_hold_bars': (50, 1000)        # Allow days for bounce
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.htf_vwap_period = int(kwargs.get('htf_vwap_period', 288))
        self.htf_ema_period = int(kwargs.get('htf_ema_period', 1440))
        self.zone_pct = float(kwargs.get('zone_pct', 0.02))
        self.vrsi_period = int(kwargs.get('vrsi_period', 20))
        self.vrsi_oversold = float(kwargs.get('vrsi_oversold', 35.0))
        self.sl_pct = float(kwargs.get('sl_pct', 0.03))
        self.tp_pct = float(kwargs.get('tp_pct', 0.08))
        self.max_hold_bars = int(kwargs.get('max_hold_bars', 200))
        
        self._s = {1: dict(entry_price=None, bars_held=0)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close = df['Close']
        open_p = df['Open']
        volume = df['Volume']

        # 1. Macro EMA
        df['macro_ema'] = talib.EMA(close, timeperiod=self.htf_ema_period)
        
        # 2. HTF VWAP
        typical = (df['High'] + df['Low'] + df['Close']) / 3.0
        rolling_tp_vol = (typical * volume).rolling(window=self.htf_vwap_period).sum()
        rolling_vol    = volume.rolling(window=self.htf_vwap_period).sum()
        df['htf_vwap'] = rolling_tp_vol / (rolling_vol + 1e-10)

        # 3. LTF V-RSI
        price_chg = close.diff()
        U = volume * price_chg.clip(lower=0)
        D = volume * (-price_chg).clip(lower=0)
        sma_u = U.rolling(window=self.vrsi_period, min_periods=self.vrsi_period).mean()
        sma_d = D.rolling(window=self.vrsi_period, min_periods=self.vrsi_period).mean()
        rs = sma_u / (sma_d + 1e-10)
        df['vrsi'] = 100.0 - (100.0 / (1.0 + rs))
        
        df.fillna(0, inplace=True)

        # --- Confirmation Logic ---
        
        # Define the Support Line (Use whichever is higher to act as the first line of defense)
        df['macro_support'] = np.maximum(df['htf_vwap'], df['macro_ema'])
        
        # Condition A: Swept Support recently
        # In the last 10 bars, did the Low price go BELOW the support line - zone_pct?
        lower_zone_bound = df['macro_support'] * (1.0 - self.zone_pct)
        was_below_support = (df['Low'] < lower_zone_bound).rolling(window=10).max() == 1.0
        
        # Condition B: V-RSI was oversold recently (exhaustion)
        was_oversold = (df['vrsi'] < self.vrsi_oversold).rolling(window=10).max() == 1.0

        # Condition C: Reclaimed Support!
        # The Close is now back ABOVE the macro_support, proving buyers stepped in.
        reclaimed_support = close > df['macro_support']
        
        # Condition D: Bullish LTF Candle (Close > Open)
        bullish_candle = close > open_p
        
        # Execution Trigger
        long_ok = was_below_support & was_oversold & reclaimed_support & bullish_candle

        signals = np.zeros(len(df), dtype=int)
        # Only enter on the exact bar the confirmation happens
        long_edge = long_ok & ~long_ok.shift(1).fillna(False)
        signals[long_edge.values] = 1

        df['signal'] = signals
        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None
            
        curr = float(row['Close'])
        s = self._s[1]
        
        if entry_price != s['entry_price']:
            s['entry_price'] = entry_price
            s['bars_held'] = 0
        
        s['bars_held'] += 1
        
        if s['bars_held'] > self.max_hold_bars:
            return 'EXIT', curr
            
        sl_price = entry_price * (1.0 - self.sl_pct)
        tp_price = entry_price * (1.0 + self.tp_pct)

        if float(row['Low'])  <= sl_price: return 'SL', sl_price

        if float(row['High']) >= tp_price: return 'TP', tp_price
            
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        # Require TP to be strictly greater than SL for a positive R:R profile
        if params.get('tp_pct', 0) <= params.get('sl_pct', 0) * 1.5:
            return False
        return True
