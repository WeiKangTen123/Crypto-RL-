import pandas as pd
import numpy as np
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class DMIADXStrategy(BaseStrategy):
    """
    DMI ADX Trend Strength Strategy.
    Enters when DI+ and DI- cross while ADX is above a strength threshold.
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.adx_period = kwargs.get('adx_period', 14)
        self.adx_threshold = kwargs.get('adx_threshold', 25.0)
        self.atr_period = kwargs.get('atr_period', 14)
        self.atr_multiplier_sl = kwargs.get('atr_multiplier_sl', 1.5)
        self.atr_multiplier_tp = kwargs.get('atr_multiplier_tp', 3.0)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. Indicators
        adx_ind = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=self.adx_period)
        df['adx'] = adx_ind.adx()
        df['di_plus'] = adx_ind.adx_pos()
        df['di_minus'] = adx_ind.adx_neg()
        
        atr_ind = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=self.atr_period)
        df['atr'] = atr_ind.average_true_range()

        # 2. Conditions
        adx_strong = df['adx'] > self.adx_threshold
        
        # Long: DI+ crosses above DI-
        long_cross = (df['di_plus'] > df['di_minus']) & (df['di_plus'].shift(1) <= df['di_minus'].shift(1))
        # Short: DI- crosses above DI+
        short_cross = (df['di_minus'] > df['di_plus']) & (df['di_minus'].shift(1) <= df['di_plus'].shift(1))

        # 3. Signals
        df['signal'] = 0
        df.loc[long_cross & adx_strong, 'signal'] = 1
        df.loc[short_cross & adx_strong, 'signal'] = -1

        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0.0,
    ) -> Tuple[str, Optional[float]]:
        
        if position == 0:
            return 'HOLD', None
            
        side = np.sign(position)
        
        sl_price = entry_price - side * (self.atr_multiplier_sl * row['atr'])
        tp_price = entry_price + side * (self.atr_multiplier_tp * row['atr'])

        if side == 1:
            if row['Low']  <= sl_price: return 'SL', sl_price

            if row['High'] >= tp_price: return 'TP', tp_price
            if row['di_minus'] > row['di_plus']:
                return 'EXIT', row['Close']
        else:
            if row['High'] >= sl_price: return 'SL', sl_price

            if row['Low']  <= tp_price: return 'TP', tp_price
            if row['di_plus'] > row['di_minus']:
                return 'EXIT', row['Close']

        return 'HOLD', None
