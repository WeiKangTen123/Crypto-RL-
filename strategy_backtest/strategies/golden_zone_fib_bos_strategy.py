import pandas as pd
import numpy as np
from strategy_backtest.base_strategy import BaseStrategy
import ta

class GoldenZoneFibBOSStrategy(BaseStrategy):
    """
    Golden Zone Fibonacci BOS Strategy.
    Identifies a structural shift (Break of Structure), waits for a retracement 
    into the 0.618 Fib level, and enters with trend.
    """
    SIGNAL_PARAMS = frozenset({'swing_window', 'fib_retrace', 'fib_ext', 'sl_fib', 'rsi_period', 'rsi_long', 'rsi_short'})

    OPTIMIZATION_RANGES = {
        'swing_window': (5, 50),
        'fib_retrace': (0.3, 0.8),
        'fib_ext': (1.1, 2.5),
        'sl_fib': (0.5, 1.5),
        'rsi_period': (5, 30),
        'rsi_long': (30, 70),
        'rsi_short': (30, 70)
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.swing_window = getattr(self, 'swing_window', 20)
        self.fib_retrace = getattr(self, 'fib_retrace', 0.618)
        self.fib_ext = getattr(self, 'fib_ext', 1.618)
        self.sl_fib = getattr(self, 'sl_fib', 0.786)
        self.rsi_period = getattr(self, 'rsi_period', 14)
        self.rsi_long = getattr(self, 'rsi_long', 50)  # Need to not be overbought
        self.rsi_short = getattr(self, 'rsi_short', 50) # Need to not be oversold

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # Calculate RSI for confirmation
        df['rsi'] = ta.momentum.RSIIndicator(df['Close'], window=self.rsi_period).rsi()
        
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        rsis = df['rsi'].values
        
        signals = np.zeros(len(df))
        tp_levels = np.zeros(len(df))
        sl_levels = np.zeros(len(df))
        
        state = 0 # 0: seeking BOS, 1: BOS Up (seeking retrace), -1: BOS Down (seeking retrace)
        
        # Initialize variables
        last_swing_low = lows[0]
        last_swing_high = highs[0]
        swing_leg_high = highs[0]
        swing_leg_low = lows[0]
        
        for i in range(self.swing_window, len(df)):
            # Update rolling recent high/low excluding current bar
            window_highs = highs[i-self.swing_window:i]
            window_lows = lows[i-self.swing_window:i]
            
            recent_high = np.max(window_highs)
            recent_low = np.min(window_lows)
            
            if state == 0:
                if closes[i] > recent_high:
                    state = 1
                    last_swing_low = recent_low
                    swing_leg_high = highs[i]
                elif closes[i] < recent_low:
                    state = -1
                    last_swing_high = recent_high
                    swing_leg_low = lows[i]
                    
            elif state == 1:
                # Update high if pushed higher
                if highs[i] > swing_leg_high:
                    swing_leg_high = highs[i]
                
                # Check for BOS Down failure
                if closes[i] < recent_low:
                    state = -1
                    last_swing_high = recent_high
                    swing_leg_low = lows[i]
                    continue
                
                # Check for retracement
                fib_level = swing_leg_high - (swing_leg_high - last_swing_low) * self.fib_retrace
                if lows[i] <= fib_level and rsis[i] < self.rsi_long:
                    signals[i] = 1
                    fib_range = swing_leg_high - last_swing_low
                    tp_levels[i] = swing_leg_high + fib_range * (self.fib_ext - 1.0)
                    sl_levels[i] = swing_leg_high - fib_range * self.sl_fib
                    state = 0 # reset
                    
            elif state == -1:
                if lows[i] < swing_leg_low:
                    swing_leg_low = lows[i]
                
                if closes[i] > recent_high:
                    state = 1
                    last_swing_low = recent_low
                    swing_leg_high = highs[i]
                    continue
                    
                fib_level = swing_leg_low + (last_swing_high - swing_leg_low) * self.fib_retrace
                if highs[i] >= fib_level and rsis[i] > self.rsi_short:
                    signals[i] = -1
                    fib_range = last_swing_high - swing_leg_low
                    tp_levels[i] = swing_leg_low - fib_range * (self.fib_ext - 1.0)
                    sl_levels[i] = swing_leg_low + fib_range * self.sl_fib
                    state = 0 # reset
        
        self.df['signal'] = signals
        self.df['tp_level'] = pd.Series(tp_levels, index=df.index).replace(0, np.nan).ffill()
        self.df['sl_level'] = pd.Series(sl_levels, index=df.index).replace(0, np.nan).ffill()
        
        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0):
        # Snapshot TP/SL on trade open so ffill() from later signals doesn't corrupt them
        if entry_price != getattr(self, '_last_entry', None):
            self._last_entry = entry_price
            self._trade_tp = getattr(row, 'tp_level', np.nan)
            self._trade_sl = getattr(row, 'sl_level', np.nan)

        tp_level = self._trade_tp
        sl_level = self._trade_sl

        if position > 0:
            tp_ok = not np.isnan(tp_level)
            sl_ok = not np.isnan(sl_level)
            if sl_ok and row.Low  <= sl_level: return 'SL', sl_level
            if tp_ok and row.High >= tp_level: return 'TP', tp_level
        elif position < 0:
            tp_ok = not np.isnan(tp_level)
            sl_ok = not np.isnan(sl_level)
            if sl_ok and row.High >= sl_level: return 'SL', sl_level
            if tp_ok and row.Low  <= tp_level: return 'TP', tp_level
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        return True
