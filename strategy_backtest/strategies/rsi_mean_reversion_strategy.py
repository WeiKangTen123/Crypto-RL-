"""
This module implements a template trading strategy based on Z-score, ATR, and EMA.
It serves as a basic example for developing new strategies within the Crypto-RL framework.
"""

from typing import Optional, Tuple

import pandas as pd

from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_rsi

class RsiMeanReversionStrategy(BaseStrategy):
    """
    A template trading strategy demonstrating the use of Z-score for mean reversion,
    filtered by EMA for trend direction, and using ATR for dynamic take profit and stop loss.
    """
    VALID_ACTIONS: frozenset = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    # Strategy specific parameters (can be optimized later)
    SIGNAL_PARAMS: frozenset = frozenset({
        'rsi_period',
        'atr_period',
        'rsi_oversold',
        'rsi_overbought',
        'tp_multiplier',
        'sl_multiplier',
    })

    def __init__(self, df: pd.DataFrame, 
                 rsi_period: int = 30, 
                 atr_period: int = 9, 
                 rsi_oversold: float = 26.9188,
                 rsi_overbought: float = 79.7836,
                 tp_multiplier: float = 5.9902,
                 sl_multiplier: float = 0.8799,
                 **kwargs):
        """
        Initializes the RsiMeanReversionStrategy with DataFrame and strategy parameters.

        Args:
            df (pd.DataFrame): The input DataFrame containing OHLCV data.
            rsi_period (int): Period for RSI calculation.
            atr_period (int): Period for ATR calculation.
            rsi_oversold (float): RSI threshold for oversold conditions (long entry).
            rsi_overbought (float): RSI threshold for overbought conditions (short entry).
            tp_multiplier (float): Multiplier for ATR to determine take profit level.
            sl_multiplier (float): Multiplier for ATR to determine stop loss level.
            **kwargs: Additional keyword arguments for the BaseStrategy.
        """
        super().__init__(df, **kwargs)
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.tp_multiplier = tp_multiplier
        self.sl_multiplier = sl_multiplier

    def generate_signals(self) -> pd.DataFrame:
        """
        Generates entry signals (long or short) based on RSI overbought/oversold conditions.

        Returns:
            pd.DataFrame: The DataFrame with an added 'signal' column (1 for long, -1 for short, 0 for neutral).
        """
        df = self.df.copy()

        # Step 1 — Compute indicators
        df['rsi'] = calc_rsi(df['Close'], self.rsi_period)
        df['atr'] = calc_atr(df, self.atr_period) # Keep ATR for trade management

        # Step 2 — Entry signals
        long_condition = (df['rsi'] < self.rsi_oversold)
        short_condition = (df['rsi'] > self.rsi_overbought)

        df['signal'] = 0
        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1

        self.df = df
        return self.df

    def manage_trade(
        self,
        row: pd.Series,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        """
        Manages open trades by determining if a take profit or stop loss condition is met.

        Args:
            row (pd.Series): The current OHLCV bar and calculated indicators.
            position (float): The current position size (positive for long, negative for short).
            entry_price (float): The price at which the position was opened.
            wallet (float): The current wallet balance.

        Returns:
            Tuple[str, Optional[float]]: A tuple containing the action ('TP', 'SL', 'HOLD')
                                         and the execution price if an action is taken.
        """

        current_atr = row['atr']

        if position > 0:  # Currently Long
            take_profit_level = entry_price + (self.tp_multiplier * current_atr)
            stop_loss_level = entry_price - (self.sl_multiplier * current_atr)
            if row['Low']  <= stop_loss_level:   return 'SL', stop_loss_level
            if row['High'] >= take_profit_level: return 'TP', take_profit_level

        elif position < 0:  # Currently Short
            take_profit_level = entry_price - (self.tp_multiplier * current_atr)
            stop_loss_level = entry_price + (self.sl_multiplier * current_atr)
            if row['High'] >= stop_loss_level:   return 'SL', stop_loss_level
            if row['Low']  <= take_profit_level: return 'TP', take_profit_level

        return 'HOLD', None
