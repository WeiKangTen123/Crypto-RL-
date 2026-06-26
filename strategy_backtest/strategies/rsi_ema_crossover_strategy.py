import pandas as pd
import numpy as np
import talib
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_rsi, calc_ema
from typing import Optional, Tuple

class RsiEmaCrossoverStrategy(BaseStrategy):
    """
    RSI & EMA Crossover Strategy.
    mode='momentum' — enter in direction of EMA cross with broad RSI gate (original)
    mode='reversal' — enter on EMA cross only when RSI is at an extreme (< oversold / > overbought)
    mode='cross_only'— pure EMA crossover, no RSI filter
    """

    OPTIMIZATION_RANGES = {
        'rsi_period':        (7,  21),
        'ema_fast':          (5,  40),   # expanded — was hitting 20 ceiling
        'ema_slow':          (30, 150),
        'rsi_oversold':      (20, 60),   # expanded — was hitting 40 ceiling
        'rsi_overbought':    (40, 80),
        'atr_period':        (5,  21),
        'atr_multiplier_sl': (0.5, 4.0),
        'mode':              ['momentum', 'reversal', 'cross_only'],
    }

    SIGNAL_PARAMS = frozenset({'rsi_period', 'ema_fast', 'ema_slow', 'mode'})

    @classmethod
    def validate_params(cls, params):
        # Prevent degenerate combos: fast must be meaningfully below slow, oversold below overbought
        if params.get('ema_fast', 9) >= params.get('ema_slow', 21) - 5:
            return False
        if params.get('rsi_oversold', 30) >= params.get('rsi_overbought', 70) - 10:
            return False
        return True

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.rsi_period        = kwargs.get('rsi_period', 14)
        self.ema_fast          = kwargs.get('ema_fast', 9)
        self.ema_slow          = kwargs.get('ema_slow', 21)
        self.rsi_oversold      = kwargs.get('rsi_oversold', 30)
        self.rsi_overbought    = kwargs.get('rsi_overbought', 70)
        self.atr_period        = kwargs.get('atr_period', 14)
        self.atr_multiplier_sl = kwargs.get('atr_multiplier_sl', 1.5)
        self.mode              = kwargs.get('mode', 'momentum')

    def generate_signals(self) -> pd.DataFrame:
        self.df['rsi']      = calc_rsi(self.df['Close'], period=self.rsi_period)
        self.df['fast_ema'] = calc_ema(self.df, period=self.ema_fast)
        self.df['slow_ema'] = calc_ema(self.df, period=self.ema_slow)
        self.df['atr']      = talib.ATR(
            self.df['High'], self.df['Low'], self.df['Close'],
            timeperiod=self.atr_period
        )

        fast = self.df['fast_ema']
        slow = self.df['slow_ema']
        rsi  = self.df['rsi']

        # Detect crossover events (rising edge only — not state)
        cross_up   = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        cross_down = (fast < slow) & (fast.shift(1) >= slow.shift(1))

        self.df['signal'] = 0

        if self.mode == 'cross_only':
            self.df.loc[cross_up,   'signal'] = 1
            self.df.loc[cross_down, 'signal'] = -1

        elif self.mode == 'reversal':
            # Enter long on cross-up only if RSI was recently oversold (< oversold threshold)
            self.df.loc[cross_up   & (rsi < self.rsi_overbought), 'signal'] = 1
            self.df.loc[cross_down & (rsi > self.rsi_oversold),   'signal'] = -1

        else:  # momentum (original)
            self.df.loc[cross_up   & (rsi < self.rsi_overbought), 'signal'] = 1
            self.df.loc[cross_down & (rsi > self.rsi_oversold),   'signal'] = -1

        return self.df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        atr = getattr(row, 'atr', None)
        if atr is None or (isinstance(atr, float) and np.isnan(atr)):
            return 'HOLD', None

        if position > 0:
            sl = entry_price - self.atr_multiplier_sl * atr
            if float(row['Low']) <= sl:
                return 'SL', sl
            fast = getattr(row, 'fast_ema', None)
            slow = getattr(row, 'slow_ema', None)
            if fast is not None and slow is not None and float(fast) < float(slow):
                return 'EXIT', None
        elif position < 0:
            sl = entry_price + self.atr_multiplier_sl * atr
            if float(row['High']) >= sl:
                return 'SL', sl
            fast = getattr(row, 'fast_ema', None)
            slow = getattr(row, 'slow_ema', None)
            if fast is not None and slow is not None and float(fast) > float(slow):
                return 'EXIT', None

        return 'HOLD', None
