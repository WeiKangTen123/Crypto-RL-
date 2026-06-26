import pandas as pd
import numpy as np
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class TimeSeriesMomentumStrategy(BaseStrategy):
    """
    Time-Series Momentum Strategy
    Identifies momentum by comparing current price to a past price over a defined period.
    """
    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        # Strategy-specific parameters
        self.momentum_period = kwargs.get("momentum_period", 20) # Period to calculate momentum
        self.momentum_threshold_entry = kwargs.get("momentum_threshold_entry", 0.005) # 0.5% price change for entry
        self.take_profit_pct = kwargs.get("take_profit_pct", 0.02) # Default TP
        self.stop_loss_pct = kwargs.get("stop_loss_pct", 0.01)   # Default SL


    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy() # Operate on a copy to avoid modifying original self.df directly

        # Calculate momentum: percentage change over momentum_period
        df['momentum'] = df['Close'].pct_change(self.momentum_period)

        df['signal'] = 0  # Default to no signal

        # --- Entry Conditions ---
        # Buy signal if momentum is positive and exceeds threshold
        buy_condition = (df['momentum'] > self.momentum_threshold_entry)
        
        # Sell signal if momentum is negative and falls below negative threshold
        sell_condition = (df['momentum'] < -self.momentum_threshold_entry)

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
