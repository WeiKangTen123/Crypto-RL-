import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy


class MeanReversionFundingRateStrategy(BaseStrategy):
    """
    Funding Rate Mean Reversion Strategy.

    This strategy aims to profit from the mean-reverting nature of perpetual
    futures funding rates. It takes long positions when funding rates are
    extremely negative (shorts pay longs) and short positions when funding rates
    are extremely positive (longs pay shorts).
    """

    # Define the parameters that can be optimized for this strategy
    SIGNAL_PARAMS = frozenset({
        "funding_threshold_long",
        "funding_threshold_short",
        "exit_threshold_long",
        "exit_threshold_short",
        "funding_lookback_period",
        "adx_period",
        "adx_threshold",
        "stop_loss_pct",
        "take_profit_pct",
    })

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)

        # Default parameters, can be overridden by kwargs
        self.funding_threshold_long = kwargs.get("funding_threshold_long", -0.0005)  # -0.05%
        self.funding_threshold_short = kwargs.get("funding_threshold_short", 0.0005) # 0.05%
        self.exit_threshold_long = kwargs.get("exit_threshold_long", 0.0001)       # 0.01%
        self.exit_threshold_short = kwargs.get("exit_threshold_short", -0.0001)     # -0.01%
        self.funding_lookback_period = kwargs.get("funding_lookback_period", 24)    # 24 hours (assuming 1h data)
        self.adx_period = kwargs.get("adx_period", 14)
        self.adx_threshold = kwargs.get("adx_threshold", 25)
        self.stop_loss_pct = kwargs.get("stop_loss_pct", 0.02)
        self.take_profit_pct = kwargs.get("take_profit_pct", 0.05)

    def generate_signals(self) -> pd.DataFrame:
        """
        Compute indicators and assign entry signals based on funding rates and ADX.
        Adds a 'signal' column: 1 = Long, -1 = Short, 0 = Neutral.
        """
        df = self.df.copy()

        # Fetch funding rate data (assuming it's already merged or available in the df)
        # In a real Freqtrade integration, this would involve dp.get_pair_dataframe(candle_type='funding_rate')
        # For this backtest, we assume 'funding_rate' column is present.
        if 'funding_rate' not in df.columns:
            raise ValueError("DataFrame must contain a 'funding_rate' column for this strategy.")

        # Calculate ADX for trend filtering
        df['ADX'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=self.adx_period)

        # Initialize signal column
        df['signal'] = 0

        # Long signal: funding rate is very negative and ADX indicates a ranging market
        long_condition = ((df['funding_rate'] < self.funding_threshold_long) &
                          (df['ADX'] < self.adx_threshold))

        # Short signal: funding rate is very positive and ADX indicates a ranging market
        short_condition = ((df['funding_rate'] > self.funding_threshold_short) &
                           (df['ADX'] < self.adx_threshold))

        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1

        self.df = df
        return self.df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        """
        Manages open positions, setting stop loss, take profit, and exit conditions.
        """
        # Funding rate mean reversion exit (close-based, checked first)
        if position > 0 and row['funding_rate'] > self.exit_threshold_long:
            return 'EXIT', None
        if position < 0 and row['funding_rate'] < self.exit_threshold_short:
            return 'EXIT', None

        if self.stop_loss_pct or self.take_profit_pct:
            sl_long  = entry_price * (1 - self.stop_loss_pct) if self.stop_loss_pct else None
            sl_short = entry_price * (1 + self.stop_loss_pct) if self.stop_loss_pct else None
            tp_long  = entry_price * (1 + self.take_profit_pct) if self.take_profit_pct else None
            tp_short = entry_price * (1 - self.take_profit_pct) if self.take_profit_pct else None

            if position > 0:
                if sl_long  is not None and row['Low']  <= sl_long:  return 'SL', sl_long
                if tp_long  is not None and row['High'] >= tp_long:  return 'TP', tp_long
            elif position < 0:
                if sl_short is not None and row['High'] >= sl_short: return 'SL', sl_short
                if tp_short is not None and row['Low']  <= tp_short: return 'TP', tp_short

        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """
        Validate strategy parameters.
        Ensures funding thresholds are correctly ordered and lookback is positive.
        """
        if params["funding_threshold_long"] >= params["funding_threshold_short"]:
            return False
        if params["funding_lookback_period"] <= 0:
            return False
        return True
