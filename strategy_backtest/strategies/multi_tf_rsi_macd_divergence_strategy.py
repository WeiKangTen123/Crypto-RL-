import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class MultiTFRSIMACDDivergenceStrategy(BaseStrategy):
    """
    Multi-TF RSI/MACD Divergence Strategy
    Category: Reversal / Momentum
    
    1. Trend Filter: Price vs 200 EMA on HTF (approximated by 800 EMA on 1H).
    2. Divergence: Regular Bullish/Bearish Divergence on RSI (Length 14).
       - Bullish: Price LL, RSI HL
       - Bearish: Price HH, RSI LH
    3. Confirmation: MACD Histogram changing sign in the direction of trade.
    """
    SIGNAL_PARAMS = frozenset({
        'htf_ema_period',
        'rsi_period',
        'macd_fast',
        'macd_slow',
        'macd_signal',
        'lookback',
        'sl_pct',
        'tp_pct',
    })

    def __init__(
        self,
        df: pd.DataFrame,
        htf_ema_period: int = 800, # Proxy for 200 EMA on 4H if using 1H data
        rsi_period: int = 15,
        macd_fast: int = 5,
        macd_slow: int = 39,
        macd_signal: int = 13,
        lookback: int = 40,
        sl_pct: float = 0.0281,
        tp_pct: float = 0.0709,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.htf_ema_period = htf_ema_period
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.lookback = lookback
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        
        self._s = {
            1:  dict(sl_price=None, tp_price=None),
            -1: dict(sl_price=None, tp_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        
        if len(df) < self.htf_ema_period:
            df['signal'] = 0
            return df
            
        df['htf_ema'] = talib.EMA(df['Close'].values, timeperiod=self.htf_ema_period)
        df['rsi'] = talib.RSI(df['Close'].values, timeperiod=self.rsi_period)
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['Close'].values, 
            fastperiod=self.macd_fast, 
            slowperiod=self.macd_slow, 
            signalperiod=self.macd_signal
        )
        
        # Identify Pivot Lows and Highs using lookback
        # A pivot low is true if RSI is lower than the past 'lookback' bars and future 'lookback' bars.
        # To avoid lookahead, we only know a pivot occurred 'lookback' bars later.
        
        # Shifted series for pivot confirmation
        # Example: lookback=5
        # The pivot happens at bar (i - lookback). 
        # So we check if rsi at (i-lookback) is the min of window [i-2*lookback : i]
        window_size = 2 * self.lookback + 1
        
        # Rolling min/max of RSI over window_size
        rsi_roll_min = df['rsi'].rolling(window=window_size, min_periods=window_size).min()
        rsi_roll_max = df['rsi'].rolling(window=window_size, min_periods=window_size).max()
        
        # Price rolling min/max over the same window
        price_roll_min = df['Low'].rolling(window=window_size, min_periods=window_size).min()
        price_roll_max = df['High'].rolling(window=window_size, min_periods=window_size).max()
        
        # A pivot low at index i-lookback is confirmed at index i
        # if rsi[i-lookback] == rsi_roll_min[i]
        df['is_pivot_low'] = df['rsi'].shift(self.lookback) == rsi_roll_min
        df['is_pivot_high'] = df['rsi'].shift(self.lookback) == rsi_roll_max
        
        # We need to track the PREVIOUS pivot to check divergence
        # Create columns to hold the value of the last pivot
        
        # Forward fill the pivot values
        df['last_pivot_low_rsi'] = np.where(df['is_pivot_low'], df['rsi'].shift(self.lookback), np.nan)
        df['last_pivot_low_price'] = np.where(df['is_pivot_low'], df['Low'].shift(self.lookback), np.nan)
        df['last_pivot_low_rsi'] = df['last_pivot_low_rsi'].ffill()
        df['last_pivot_low_price'] = df['last_pivot_low_price'].ffill()
        
        # The 'previous' pivot is the one before the current last_pivot
        # We can get this by shifting before the ffill update, but we only want to update on new pivots.
        df['prev_pivot_low_rsi'] = df['last_pivot_low_rsi'].shift(1).where(df['is_pivot_low']).ffill()
        df['prev_pivot_low_price'] = df['last_pivot_low_price'].shift(1).where(df['is_pivot_low']).ffill()

        # Same for high pivots
        df['last_pivot_high_rsi'] = np.where(df['is_pivot_high'], df['rsi'].shift(self.lookback), np.nan)
        df['last_pivot_high_price'] = np.where(df['is_pivot_high'], df['High'].shift(self.lookback), np.nan)
        df['last_pivot_high_rsi'] = df['last_pivot_high_rsi'].ffill()
        df['last_pivot_high_price'] = df['last_pivot_high_price'].ffill()
        
        df['prev_pivot_high_rsi'] = df['last_pivot_high_rsi'].shift(1).where(df['is_pivot_high']).ffill()
        df['prev_pivot_high_price'] = df['last_pivot_high_price'].shift(1).where(df['is_pivot_high']).ffill()

        # Bullish Divergence: Price LL, RSI HL
        # We check this AT the time a new pivot is confirmed
        df['bull_div'] = (
            df['is_pivot_low'] &
            (df['last_pivot_low_price'] < df['prev_pivot_low_price']) &
            (df['last_pivot_low_rsi'] > df['prev_pivot_low_rsi'])
        )
        
        # Bearish Divergence: Price HH, RSI LH
        df['bear_div'] = (
            df['is_pivot_high'] &
            (df['last_pivot_high_price'] > df['prev_pivot_high_price']) &
            (df['last_pivot_high_rsi'] < df['prev_pivot_high_rsi'])
        )
        
        # We carry the divergence signal forward for a short window (e.g. lookback bars) to wait for MACD confirmation
        df['bull_div_active'] = df['bull_div'].rolling(window=self.lookback, min_periods=1).max().astype(bool)
        df['bear_div_active'] = df['bear_div'].rolling(window=self.lookback, min_periods=1).max().astype(bool)
        
        # HTF Trend
        df['is_uptrend'] = df['Close'] > df['htf_ema']
        df['is_downtrend'] = df['Close'] < df['htf_ema']
        
        # MACD Confirmation (Hist turning positive/negative)
        df['macd_hist_up'] = (df['macd_hist'] > 0) & (df['macd_hist'].shift(1) <= 0)
        df['macd_hist_down'] = (df['macd_hist'] < 0) & (df['macd_hist'].shift(1) >= 0)
        
        # Signals
        df['signal'] = 0
        long_cond = df['bull_div_active'] & df['is_uptrend'] & df['macd_hist_up']
        short_cond = df['bear_div_active'] & df['is_downtrend'] & df['macd_hist_down']
        
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1

        self.df = df
        return self.df

    def manage_trade(
        self,
        row: pd.Series,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        direction = np.sign(position)
        state = self._s[direction]
        
        if state['sl_price'] is None:
            if direction > 0:
                state['sl_price'] = entry_price * (1 - self.sl_pct)
                state['tp_price'] = entry_price * (1 + self.tp_pct)
            else:
                state['sl_price'] = entry_price * (1 + self.sl_pct)
                state['tp_price'] = entry_price * (1 - self.tp_pct)
                
        if direction > 0:
            if row.Low <= state['sl_price']:
                sl = state['sl_price']; state['sl_price'] = None; return 'SL', sl
            if row.High >= state['tp_price']:
                tp = state['tp_price']; state['sl_price'] = None; return 'TP', tp
        else:
            if row.High >= state['sl_price']:
                sl = state['sl_price']; state['sl_price'] = None; return 'SL', sl
            if row.Low <= state['tp_price']:
                tp = state['tp_price']; state['sl_price'] = None; return 'TP', tp
                
        return 'HOLD', None
