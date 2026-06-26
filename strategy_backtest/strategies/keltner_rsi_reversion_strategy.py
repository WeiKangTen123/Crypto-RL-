import pandas as pd
import numpy as np
import ta
from strategy_backtest.base_strategy import BaseStrategy
from typing import Tuple, Optional

class KeltnerRSIReversionStrategy(BaseStrategy):
    """
    Keltner Channel RSI Reversion Strategy
    Identifies oversold/overbought conditions in range-bound or choppy markets
    using Keltner Channels for volatility bands and RSI for momentum exhaustion.
    """

    OPTIMIZATION_RANGES = {
        'kc_window': (10, 50),
        'kc_multiplier': (1.0, 6.0),
        'kc_atr_window': (5, 30),
        'rsi_window': (5, 30),
        'rsi_oversold': (15, 45),
        'rsi_overbought': (55, 85),
        'sl_atr_multiplier': (0.5, 3.0),
        'confirmation_mode': ['RSI_ONLY', 'VOLUME_EXHAUSTION', 'BOTH']
    }

    SIGNAL_PARAMS = frozenset({
        'kc_window', 'kc_multiplier', 'kc_atr_window', 
        'rsi_window', 'rsi_oversold', 'rsi_overbought', 
        'sl_atr_multiplier', 'confirmation_mode'
    })

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.kc_window = kwargs.get('kc_window', 20)
        self.kc_multiplier = kwargs.get('kc_multiplier', 2.0)
        self.kc_atr_window = kwargs.get('kc_atr_window', 10)
        self.rsi_window = kwargs.get('rsi_window', 14)
        self.rsi_oversold = kwargs.get('rsi_oversold', 30.0)
        self.rsi_overbought = kwargs.get('rsi_overbought', 70.0)
        self.sl_atr_multiplier = kwargs.get('sl_atr_multiplier', 1.0)
        self.confirmation_mode = kwargs.get('confirmation_mode', 'RSI_ONLY')

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        
        # Calculate RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['Close'], window=self.rsi_window).rsi()
        
        # Calculate Keltner Channels
        kc = ta.volatility.KeltnerChannel(
            high=df['High'], low=df['Low'], close=df['Close'],
            window=self.kc_window, window_atr=self.kc_atr_window,
            original_version=False, multiplier=self.kc_multiplier
        )
        df['kc_upper'] = kc.keltner_channel_hband()
        df['kc_middle'] = kc.keltner_channel_mband()
        df['kc_lower'] = kc.keltner_channel_lband()
        
        # Calculate ATR for stop loss
        df['atr'] = ta.volatility.AverageTrueRange(
            high=df['High'], low=df['Low'], close=df['Close'], window=self.kc_atr_window
        ).average_true_range()
        
        # Volume Exhaustion (Spike compared to average)
        df['vol_ma'] = df['Volume'].rolling(window=20).mean()
        df['vol_spike'] = df['Volume'] > (df['vol_ma'] * 1.5)

        df['signal'] = 0
        df['entry_atr'] = 0.0
        
        # Base Reversion conditions
        band_long = df['Close'] < df['kc_lower']
        band_short = df['Close'] > df['kc_upper']
        
        rsi_long = df['rsi'] < self.rsi_oversold
        rsi_short = df['rsi'] > self.rsi_overbought

        if self.confirmation_mode == 'RSI_ONLY':
            long_cond = band_long & rsi_long
            short_cond = band_short & rsi_short
        elif self.confirmation_mode == 'VOLUME_EXHAUSTION':
            long_cond = band_long & df['vol_spike']
            short_cond = band_short & df['vol_spike']
        else: # BOTH
            long_cond = band_long & rsi_long & df['vol_spike']
            short_cond = band_short & rsi_short & df['vol_spike']
        
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1
        df.loc[long_cond | short_cond, 'entry_atr'] = df['atr']
        
        # Forward fill entry_atr so manage_trade can access it from row
        df['entry_atr'] = df['entry_atr'].replace(0.0, np.nan).ffill()
        
        return df.astype({'signal': int})

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        entry_atr = getattr(row, 'entry_atr', 0)
        
        # Fallback if entry_atr is missing or 0
        if pd.isna(entry_atr) or entry_atr == 0:
            entry_atr = entry_price * 0.02
            
        if position > 0:
            sl_price = entry_price - (self.sl_atr_multiplier * entry_atr)
            if row['Low']  <= sl_price: return 'SL', sl_price

            if row['High'] >= row['kc_middle']: return 'TP', row['kc_middle']
        elif position < 0:
            sl_price = entry_price + (self.sl_atr_multiplier * entry_atr)
            if row['High'] >= sl_price: return 'SL', sl_price

            if row['Low']  <= row['kc_middle']: return 'TP', row['kc_middle']
                
        return 'HOLD', None
