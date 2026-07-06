import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict


class MultiCoinBaseStrategy(ABC):
    """
    Abstract base class for all rule-based multi-coin (portfolio) backtest strategies.

    Subclasses receive a dictionary of raw OHLCV DataFrames via __init__ and must implement:
      - generate_signals() : annotate the dfs with a 'signal' column for each coin
      - manage_trade()     : decide whether to exit an open position each bar per coin
    """

    VALID_ACTIONS: frozenset = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})
    SIGNAL_PARAMS: frozenset = frozenset()

    def __init__(self, dfs: Dict[str, pd.DataFrame], **kwargs):
        self.dfs = {sym: df.copy() for sym, df in dfs.items()}
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def generate_signals(self) -> Dict[str, pd.DataFrame]:
        """
        Compute indicators and assign entry signals.
        Must add a 'signal' column: 1 = Long, -1 = Short, 0 = Neutral for each df in self.dfs.
        Returns self.dfs.
        """
        pass

    @abstractmethod
    def manage_trade(
        self,
        symbol: str,
        row: pd.Series,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        """
        Called every bar for each open position for a specific symbol.

        Parameters
        ----------
        symbol      : string name of the coin (e.g., 'BTCUSDT')
        row         : current OHLCV bar for that coin
        position    : signed qty — positive for long, negative for short
        entry_price : fill price when the position was opened
        wallet      : balance at entry (for SL sizing)

        Returns
        -------
        (action, exec_price)
        """
        pass

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """Return False to skip a parameter combination in the optimizer."""
        return True
