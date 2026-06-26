import pandas as pd
import numpy as np
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import detect_order_blocks

class SMCOrderBlockReversal(BaseStrategy):
    """
    Order Block (SMC) Reversal Strategy
    Identifies Order Blocks and enters on mitigation.
    """

    OPTIMIZATION_RANGES = {
        'atr_period': (5, 30),
        'atr_multiplier': (1.0, 5.0),
        'tp_pct': (0.01, 0.20),
        'sl_pct': (0.01, 0.10),
        'entry_mode': ['CONSERVATIVE', 'AGGRESSIVE'],
        'mitigation_type': ['TOUCH', 'CLOSE_INSIDE'],
        'trend_filter': ['EMA200', 'NONE']
    }

    SIGNAL_PARAMS = frozenset({
        'atr_period', 'atr_multiplier', 'tp_pct', 'sl_pct', 
        'entry_mode', 'mitigation_type', 'trend_filter'
    })

    def __init__(self, df: pd.DataFrame, **kwargs):
        self.atr_period = kwargs.get('atr_period', 14)
        self.atr_multiplier = kwargs.get('atr_multiplier', 2.0)
        self.tp_pct = kwargs.get('tp_pct', 0.06)
        self.sl_pct = kwargs.get('sl_pct', 0.02)
        self.entry_mode = kwargs.get('entry_mode', 'AGGRESSIVE')
        self.mitigation_type = kwargs.get('mitigation_type', 'TOUCH')
        self.trend_filter = kwargs.get('trend_filter', 'NONE')
        super().__init__(df, **kwargs)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        import talib
        
        # Ensure lowercase columns exist for library function
        df['open'] = df['Open']
        df['high'] = df['High']
        df['low'] = df['Low']
        df['close'] = df['Close']
        
        # Detect OB signals from library
        df['signal'] = detect_order_blocks(
            df, 
            atr_period=self.atr_period, 
            atr_multiplier=self.atr_multiplier
        )

        # ── Logic Switches ──────────────────────────────────────────────────
        
        # 1. Trend Filter
        if self.trend_filter == 'EMA200':
            ema200 = talib.EMA(df['Close'], timeperiod=200)
            df.loc[(df['signal'] == 1) & (df['Close'] < ema200), 'signal'] = 0
            df.loc[(df['signal'] == -1) & (df['Close'] > ema200), 'signal'] = 0

        # 2. Entry Mode
        if self.entry_mode == 'CONSERVATIVE':
            df['rsi'] = talib.RSI(df['Close'], timeperiod=14)
            df.loc[(df['signal'] == 1) & (df['rsi'] > 35), 'signal'] = 0
            df.loc[(df['signal'] == -1) & (df['rsi'] < 65), 'signal'] = 0
        
        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        if position > 0:
            sl_price = entry_price * (1 - self.sl_pct)
            tp_price = entry_price * (1 + self.tp_pct)
            if row['Low']  <= sl_price: return 'SL', sl_price

            if row['High'] >= tp_price: return 'TP', tp_price
        elif position < 0:
            sl_price = entry_price * (1 + self.sl_pct)
            tp_price = entry_price * (1 - self.tp_pct)
            if row['High'] >= sl_price: return 'SL', sl_price

            if row['Low']  <= tp_price: return 'TP', tp_price
                
        return 'HOLD', None
