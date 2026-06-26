import pandas as pd
import numpy as np
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_zscore, calc_atr, calc_ema,
    detect_candle_hammer, detect_candle_engulfing,
    detect_candle_bearish_engulfing, detect_candle_shooting_star
)

class ZScoreStatArbStrategy(BaseStrategy):
    """
    Z-Score Statistical Arbitrage Strategy.
    Mean-reversion based on standard deviations from the rolling mean.
    Confirmed by candle patterns and filtered by regime trend.
    """
    
    SIGNAL_PARAMS = frozenset({
        "z_period", "z_threshold", "use_candle_confirm", "trend_filter_period"
    })

    OPTIMIZATION_RANGES = {
        "z_period": (10, 100),
        "z_threshold": (1.5, 4.5),
        "sl_atr_mult": (1.0, 5.0),
        "use_candle_confirm": [True, False],
        "trend_filter_period": [0, 50, 100, 200] # 0 means disabled
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        # Default parameters
        self.z_period = 20
        self.z_threshold = 3.0
        self.sl_atr_mult = 3.0
        self.use_candle_confirm = True
        self.trend_filter_period = 200
        
        super().__init__(df, **kwargs)
        
        # Risk / Exit State
        self._s = {"entry_price": 0, "sl": 0, "tp": 0}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Indicators
        df['zscore'] = calc_zscore(df['Close'], period=self.z_period)
        df['atr'] = calc_atr(df, period=14)
        
        # 2. Candle Patterns
        df['bull_confirm'] = detect_candle_hammer(df) | detect_candle_engulfing(df)
        df['bear_confirm'] = detect_candle_shooting_star(df) | detect_candle_bearish_engulfing(df)
        
        # 3. Regime Filter (Trend)
        if self.trend_filter_period > 0:
            df['ema_trend'] = calc_ema(df, period=self.trend_filter_period)
            df['trend_up'] = df['Close'] > df['ema_trend']
            df['trend_down'] = df['Close'] < df['ema_trend']
        else:
            df['trend_up'] = True
            df['trend_down'] = True

        # 4. Signal Logic
        df['signal'] = 0
        
        # Long conditions: zscore < -threshold + (optional confirm) + (optional trend)
        long_mask = (df['zscore'] < -self.z_threshold)
        if self.use_candle_confirm:
            long_mask &= df['bull_confirm']
        long_mask &= df['trend_up']
        
        # Short conditions: zscore > threshold + (optional confirm) + (optional trend)
        short_mask = (df['zscore'] > self.z_threshold)
        if self.use_candle_confirm:
            short_mask &= df['bear_confirm']
        short_mask &= df['trend_down']
        
        df.loc[long_mask, 'signal'] = 1
        df.loc[short_mask, 'signal'] = -1
        
        self.df = df
        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0):
        """
        Exit when Z-Score returns to mean (0) or hits SL (ATR-based).
        """
        # Detection of new trade
        if entry_price != self._s['entry_price']:
            self._s['entry_price'] = entry_price
            atr = row['atr']
            if position > 0:
                self._s['sl'] = entry_price - (self.sl_atr_mult * atr)
            else:
                self._s['sl'] = entry_price + (self.sl_atr_mult * atr)

        z = row['zscore']

        if position > 0:  # Long
            # Take Profit: Mean reversion (z-score based — Close is correct here)
            if z >= 0:
                return 'EXIT', None
            # Stop Loss — use Low (wick can hit SL)
            if row['Low'] <= self._s['sl']:
                return 'SL', self._s['sl']
        elif position < 0:  # Short
            # Take Profit: Mean reversion (z-score based — Close is correct here)
            if z <= 0:
                return 'EXIT', None
            # Stop Loss — use High (wick can hit SL)
            if row['High'] >= self._s['sl']:
                return 'SL', self._s['sl']
                
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """Basic validation if needed."""
        return True
