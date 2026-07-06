import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any


class BaseStrategy(ABC):
    """
    Abstract base class for all rule-based backtest strategies.

    Subclasses receive the raw OHLCV DataFrame via __init__ and must implement:
      - generate_signals() : annotate the df with a 'signal' column
      - manage_trade()     : decide whether to exit an open position each bar

    manage_trade CONTRACT
    ---------------------
    action     : 'SL' | 'TP' | 'REVERSE' | 'EXIT' | 'HOLD' | 'ADD' | 'SKIP'
    exec_price : exact fill price for SL/TP, or None to use bar Close
    """

    VALID_ACTIONS: frozenset = frozenset({'SL', 'TP', 'TS', 'REVERSE', 'EXIT', 'HOLD', 'ADD', 'SKIP'})
    SIGNAL_PARAMS: frozenset = frozenset()

    def __init__(self, df: pd.DataFrame, **kwargs) -> None:
        self.df: pd.DataFrame = df.copy()
        self._state: Dict[str, Any] = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def generate_signals(self) -> pd.DataFrame:
        """
        Compute indicators and assign entry signals.
        Must add a 'signal' column: 1 = Long, -1 = Short, 0 = Neutral.
        Returns self.df.
        """
        pass

    @abstractmethod
    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        """
        Called every bar for each open position.

        Parameters
        ----------
        row         : current OHLCV bar
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
