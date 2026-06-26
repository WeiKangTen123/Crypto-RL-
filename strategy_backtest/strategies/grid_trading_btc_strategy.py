import pandas as pd
import numpy as np
from strategy_backtest.base_strategy import BaseStrategy
from typing import Optional, Tuple


class GridTradingBTCStrategy(BaseStrategy):
    """
    A simple grid trading strategy for BTC.
    Places buy and sell orders at predefined price levels (grid).
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.grid_levels = kwargs.get('grid_levels', [28000, 29000, 30000, 31000, 32000])
        self.grid_spacing = kwargs.get('grid_spacing', 1000)
        self.order_size = kwargs.get('order_size', 0.001) # BTC quantity
        self.initial_balance = kwargs.get('initial_balance', 10000) # USD
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.05)
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.03) # Added take_profit_pct
        # Ensure grid_levels are sorted
        self.grid_levels.sort()

    def generate_signals(self) -> pd.DataFrame:
        """
        Generates entry and exit signals based on price crossing grid levels.
        For a simple grid, signals are generated when price crosses a grid level.
        """
        self.df['signal'] = 0

        # Initialize current_price, previous_price for signal generation
        # This is a simplified approach, a real grid strategy would manage multiple open orders
        # For backtesting, we'll simulate opening a position when price enters a grid.

        # Simplified signal generation:
        # If price goes below a grid level, buy (long signal)
        # If price goes above a grid level, sell (short signal)
        # This is a highly simplified representation for initial prototyping.
        # A true grid would involve placing multiple limit orders.

        # Placeholder logic: for now, we'll just indicate if price is within the grid.
        # This will be refined in manage_trade to reflect actual grid mechanics.
        # We will generate signals based on a mean reversion idea for now.
        # If price falls below the lowest grid level, generate a buy signal.
        # If price rises above the highest grid level, generate a sell signal.

        if not self.df.empty:
            for i in range(1, len(self.df)):
                current_close = self.df['Close'].iloc[i]
                prev_close = self.df['Close'].iloc[i-1]

                # Buy signal: if price crosses below a grid level
                for level in self.grid_levels:
                    if prev_close >= level and current_close < level:
                        self.df.loc[self.df.index[i], 'signal'] = 1 # Long signal

                # Sell signal: if price crosses above a grid level
                for level in self.grid_levels:
                    if prev_close <= level and current_close > level:
                        self.df.loc[self.df.index[i], 'signal'] = -1 # Short signal

        return self.df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        """
        Manages open positions based on grid levels.
        In a real grid, this would close positions as price moves between levels.
        For this prototype, it will just manage existing long/short positions.
        """
        # If holding a long position
        if position > 0:
            tp_price = entry_price * (1 + self.take_profit_pct)
            sl_price = entry_price * (1 - self.stop_loss_pct)
            if row['Low']  <= sl_price: return ('SL', sl_price)
            if row['High'] >= tp_price: return ('TP', tp_price)

        # If holding a short position
        elif position < 0:
            tp_price = entry_price * (1 - self.take_profit_pct)
            sl_price = entry_price * (1 + self.stop_loss_pct)
            if row['High'] >= sl_price: return ('SL', sl_price)
            if row['Low']  <= tp_price: return ('TP', tp_price)
        
        return ('HOLD', None)

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """
        Validate parameters for the grid trading strategy.
        Ensures grid_levels is a sorted list of at least 2 levels.
        """
        grid_levels = params.get('grid_levels')
        grid_spacing = params.get('grid_spacing')
        order_size = params.get('order_size')
        stop_loss_pct = params.get('stop_loss_pct')
        take_profit_pct = params.get('take_profit_pct') # Validate take_profit_pct

        if not isinstance(grid_levels, list) or len(grid_levels) < 2:
            return False
        if not all(isinstance(x, (int, float)) for x in grid_levels):
            return False
        if not all(grid_levels[i] < grid_levels[i+1] for i in range(len(grid_levels)-1)):
            return False # Ensure grid levels are sorted ascending

        if not isinstance(grid_spacing, (int, float)) or grid_spacing <= 0:
            return False
        if not isinstance(order_size, (int, float)) or order_size <= 0:
            return False
        if not isinstance(stop_loss_pct, (int, float)) or not (0 < stop_loss_pct < 1):
            return False
        if not isinstance(take_profit_pct, (int, float)) or not (0 < take_profit_pct < 1): # Validate take_profit_pct
            return False
            
        return True
