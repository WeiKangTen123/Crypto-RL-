import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class TrendIntensityIndexStrategy(BaseStrategy):
    """
    Trend Intensity Index (TII) Strategy
    
    Logic:
      - TII: Measures the percentage of positive deviations from a mean.
      - Entry: TII crosses 80 (Long) or 20 (Short).
      - Filter: 200 SMA for macro trend.
    """

    SIGNAL_PARAMS = frozenset([
        'major_period', 'minor_period', 'tii_upper', 'tii_lower',
        'sma_macro_period', 'atr_period'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        major_period: int = 60,
        minor_period: int = 30,
        tii_upper: float = 80.0,
        tii_lower: float = 20.0,
        sma_macro_period: int = 200,
        atr_period: int = 14,
        tp_rr: float = 2.0,
        sl_atr_mult: float = 2.0,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.major_period = major_period
        self.minor_period = minor_period
        self.tii_upper = tii_upper
        self.tii_lower = tii_lower
        self.sma_macro_period = sma_macro_period
        self.atr_period = atr_period
        self.tp_rr = tp_rr
        self.sl_atr_mult = sl_atr_mult

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close = df['Close']
        
        # 1. TII Calculation
        ma = close.rolling(window=self.major_period).mean()
        dev = close - ma
        
        pos_dev = dev.clip(lower=0)
        neg_dev = dev.clip(upper=0).abs()
        
        sd_plus = pos_dev.rolling(window=self.minor_period).sum()
        sd_minus = neg_dev.rolling(window=self.minor_period).sum()
        
        df['tii'] = 100 * sd_plus / (sd_plus + sd_minus)
        
        # 2. SMA Macro Filter
        df['sma_200'] = ta.trend.sma_indicator(close, window=self.sma_macro_period)
        
        # 3. ATR for Risk Management
        df['ATR'] = ta.volatility.average_true_range(
            high=df['High'], low=df['Low'], close=df['Close'], window=self.atr_period
        )
        
        # 4. Signal Logic
        long_cond = (df['tii'] > self.tii_upper) & (df['tii'].shift(1) <= self.tii_upper) & (close > df['sma_200'])
        short_cond = (df['tii'] < self.tii_lower) & (df['tii'].shift(1) >= self.tii_lower) & (close < df['sma_200'])
        
        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1
        signals[short_cond] = -1
        
        df['signal'] = signals
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        atr = getattr(row, 'ATR', 0)
        
        if side == 1:
            sl_price = entry_price - self.sl_atr_mult * atr if atr > 0 else entry_price * 0.95
            tp_price = entry_price + (entry_price - sl_price) * self.tp_rr
            if float(row['Low'])  <= sl_price: return 'SL', sl_price

            if float(row['High']) >= tp_price: return 'TP', tp_price

        elif side == -1:
            sl_price = entry_price + self.sl_atr_mult * atr if atr > 0 else entry_price * 1.05
            tp_price = entry_price - (sl_price - entry_price) * self.tp_rr
            if float(row['High']) >= sl_price: return 'SL', sl_price

            if float(row['Low'])  <= tp_price: return 'TP', tp_price

        return 'HOLD', None
