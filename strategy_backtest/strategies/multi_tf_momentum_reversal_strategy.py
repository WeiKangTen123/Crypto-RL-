import pandas as pd
import numpy as np
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class MultiTFMomentumReversalStrategy(BaseStrategy):
    """
    Multi-Timeframe Momentum-Reversal Strategy
    Leverages short-term momentum and long-term reversal, filtering with Williams %R, TSI, and CHOP.
    """
    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        # Strategy-specific parameters
        self.short_momentum_period = kwargs.get("short_momentum_period", 20) # For short-term momentum signal
        self.long_reversal_period = kwargs.get("long_reversal_period", 100)  # For long-term reversal signal
        self.williams_r_period = kwargs.get("williams_r_period", 14)
        self.tsi_fast_period = kwargs.get("tsi_fast_period", 13)
        self.tsi_slow_period = kwargs.get("tsi_slow_period", 25)
        self.chop_period = kwargs.get("chop_period", 14)
        self.momentum_threshold_entry = kwargs.get("momentum_threshold_entry", 0.01) # 1% price change
        self.reversal_threshold_entry = kwargs.get("reversal_threshold_entry", 0.05) # 5% price change
        self.williams_r_oversold = kwargs.get("williams_r_oversold", -80)
        self.williams_r_overbought = kwargs.get("williams_r_overbought", -20)
        self.tsi_oversold = kwargs.get("tsi_oversold", -20)
        self.tsi_overbought = kwargs.get("tsi_overbought", 20)
        self.chop_overbought = kwargs.get("chop_overbought", 61.8) # Gold ratio for chop overbought
        self.chop_oversold = kwargs.get("chop_oversold", 38.2) # Gold ratio for chop oversold
        self.take_profit_pct = kwargs.get("take_profit_pct", 0.02) # Default TP
        self.stop_loss_pct = kwargs.get("stop_loss_pct", 0.01)   # Default SL


    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy() # Operate on a copy to avoid modifying original self.df directly

        # --- Calculate Indicators ---
        # Short-term Momentum (e.g., simple price change)
        df['short_momentum'] = df['Close'].pct_change(self.short_momentum_period)

        # Long-term momentum: past N-bar return (backward-looking only, no future shift)
        df['long_reversal'] = df['Close'].pct_change(self.long_reversal_period)

        # Williams %R
        df['williams_r'] = ((df['High'].rolling(self.williams_r_period).max() - df['Close']) / \
                           (df['High'].rolling(self.williams_r_period).max() - df['Low'].rolling(self.williams_r_period).min())) * -100

        # True Strength Index (TSI)
        def _calculate_tsi(price_series, fast_period, slow_period):
            diff = price_series.diff()
            abs_diff = abs(price_series.diff())
            ema_diff = diff.ewm(span=fast_period, adjust=False).mean().ewm(span=slow_period, adjust=False).mean()
            ema_abs_diff = abs_diff.ewm(span=fast_period, adjust=False).mean().ewm(span=slow_period, adjust=False).mean()
            tsi = (ema_diff / ema_abs_diff) * 100
            return tsi.fillna(0) # Fill NaN from initial EMA calculations

        df['tsi'] = _calculate_tsi(df['Close'], self.tsi_fast_period, self.tsi_slow_period)

        # Choppiness Index (CHOP) - Simplified version for prototyping
        # True Range
        high_low = df['High'] - df['Low']
        high_prev_close = abs(df['High'] - df['Close'].shift(1))
        low_prev_close = abs(df['Low'] - df['Close'].shift(1))
        df['tr'] = pd.DataFrame({'high_low': high_low, 'high_prev_close': high_prev_close, 'low_prev_close': low_prev_close}).max(axis=1)
        df['atr'] = df['tr'].rolling(self.chop_period).mean()
        hl_range = df['High'].rolling(self.chop_period).max() - df['Low'].rolling(self.chop_period).min()
        hl_range = hl_range.replace(0, np.nan)  # guard against flat/gapped markets
        df['chop'] = 100 * np.log10(df['atr'] / hl_range) / np.log10(self.chop_period)
        df['chop'] = df['chop'].fillna(0).replace([np.inf, -np.inf], 0)

        df['signal'] = 0  # Default to no signal

        # --- Entry Conditions ---
        # Example: Buy on short-term momentum confirmed by Williams %R oversold and low choppiness (trending)
        buy_condition = (df['williams_r'] < self.williams_r_oversold)

        # Example: Sell on long-term reversal confirmed by Williams %R overbought and high choppiness (ranging)
        sell_condition = (df['williams_r'] > self.williams_r_overbought)


        df.loc[buy_condition, 'signal'] = 1  # Buy signal
        df.loc[sell_condition, 'signal'] = -1 # Sell signal

        self.df = df # Update self.df with the modified DataFrame
        return self.df

    def manage_trade(self, row: pd.Series, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        # For simplicity, assuming a positive position is 'long' and negative is 'short'
        if position > 0: # Long position
            # Check for take profit
            if row['High'] >= entry_price * (1 + self.take_profit_pct):
                return 'EXIT', entry_price * (1 + self.take_profit_pct)
            # Check for stop loss
            elif row['Low'] <= entry_price * (1 - self.stop_loss_pct):
                return 'EXIT', entry_price * (1 - self.stop_loss_pct)
        elif position < 0: # Short position
            # Check for take profit
            if row['Low'] <= entry_price * (1 - self.take_profit_pct):
                return 'EXIT', entry_price * (1 - self.take_profit_pct)
            # Check for stop loss
            elif row['High'] >= entry_price * (1 + self.stop_loss_pct):
                return 'EXIT', entry_price * (1 + self.stop_loss_pct)
        return 'HOLD', None
