import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class ZeroLagTrendSpeedStrategy(BaseStrategy):
    """
    Zero-Lag Trend Speed Momentum Strategy.
    Combines ZLEMA with velocity (Slope 1) and acceleration (Slope 2) of price action.
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.zlema_period = kwargs.get('zlema_period', 20)
        self.ema_speed_period = kwargs.get('ema_speed_period', 5)
        self.zscore_period = kwargs.get('zscore_period', 100)
        self.zscore_threshold = kwargs.get('zscore_threshold', 1.5)
        self.atr_period = kwargs.get('atr_period', 14)
        self.atr_multiplier_sl = kwargs.get('atr_multiplier_sl', 1.5)
        self.atr_multiplier_tp = kwargs.get('atr_multiplier_tp', 3.0)
        
        # New Enhancements
        self.direction_mode = kwargs.get('direction_mode', 'both')
        self.use_adx_filter = kwargs.get('use_adx_filter', True)
        self.adx_period = kwargs.get('adx_period', 14)
        self.adx_threshold = kwargs.get('adx_threshold', 25)
        self.exit_mode = kwargs.get('exit_mode', 'dynamic')
        self.use_taker_filter = kwargs.get('use_taker_filter', False)
        self.taker_threshold = kwargs.get('taker_threshold', 0.55)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. Zero-Lag EMA (ZLEMA)
        lag = (self.zlema_period - 1) // 2
        data_lag = df['Close'] + (df['Close'] - df['Close'].shift(lag))
        df['zlema'] = talib.EMA(data_lag.fillna(df['Close']), timeperiod=self.zlema_period)

        # 2. Trend Speed (Velocity & Acceleration)
        df['fast_ema'] = talib.EMA(df['Close'], timeperiod=self.ema_speed_period)
        df['velocity'] = df['fast_ema'].diff()
        df['acceleration'] = df['velocity'].diff()

        # 3. Momentum Z-Score
        df['price_change'] = df['Close'].diff()
        df['mom_mean'] = df['price_change'].rolling(window=self.zscore_period).mean()
        df['mom_std'] = df['price_change'].rolling(window=self.zscore_period).std()
        df['mom_zscore'] = (df['price_change'] - df['mom_mean']) / df['mom_std']

        # 4. ADX Filter
        df['adx'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=self.adx_period)
        vol_ok = df['adx'] > self.adx_threshold if self.use_adx_filter else True

        # 5. Taker Flow Filter (BTC Taker Flow proxy if available)
        taker_ok_long = True
        taker_ok_short = True
        if self.use_taker_filter and 'taker_buy_base_asset_volume' in df.columns:
            # Simple Taker Ratio: Buy Vol / Total Vol
            df['taker_ratio'] = df['taker_buy_base_asset_volume'] / df['Volume']
            taker_ok_long = df['taker_ratio'] > self.taker_threshold
            taker_ok_short = df['taker_ratio'] < (1.0 - self.taker_threshold)

        # 6. ATR for SL/TP
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.atr_period)

        df.fillna(0, inplace=True)

        # 7. Entry Signals
        long_condition = (
            (df['Close'] > df['zlema']) &
            (df['velocity'] > 0) &
            (df['acceleration'] > 0) &
            (df['mom_zscore'] > self.zscore_threshold) &
            vol_ok & taker_ok_long
        )
        
        short_condition = (
            (df['Close'] < df['zlema']) &
            (df['velocity'] < 0) &
            (df['acceleration'] < 0) &
            (df['mom_zscore'] < -self.zscore_threshold) &
            vol_ok & taker_ok_short
        )

        df['signal'] = 0
        if self.direction_mode in ['both', 'long_only']:
            df.loc[long_condition, 'signal'] = 1
        if self.direction_mode in ['both', 'short_only']:
            df.loc[short_condition, 'signal'] = -1

        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        # 1. Hard SL/TP
        tp_price = entry_price + (self.atr_multiplier_tp * row['atr']) if position > 0 else entry_price - (self.atr_multiplier_tp * row['atr'])
        sl_price = entry_price - (self.atr_multiplier_sl * row['atr']) if position > 0 else entry_price + (self.atr_multiplier_sl * row['atr'])
        
        if position > 0:
            if row['Low']  < sl_price: return 'SL', sl_price
            if row['High'] > tp_price: return 'TP', tp_price
        else:
            if row['High'] > sl_price: return 'SL', sl_price
            if row['Low']  < tp_price: return 'TP', tp_price

        # 2. Dynamic Exits (Optional)
        if self.exit_mode == 'dynamic':
            if position > 0:
                if (row['velocity'] > 0 and row['acceleration'] < 0) or (row['Close'] < row['zlema']):
                    return 'EXIT', row['Close']
            else:
                if (row['velocity'] < 0 and row['acceleration'] > 0) or (row['Close'] > row['zlema']):
                    return 'EXIT', row['Close']
                
        return 'HOLD', None
                
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        return True

    OPTIMIZATION_RANGES = {
        'direction_mode': ['both', 'long_only', 'short_only'],
        'use_adx_filter': [True, False],
        'adx_period': (10, 40),
        'adx_threshold': (15, 45),
        'exit_mode': ['dynamic', 'fixed_only'],
        'zlema_period': (10, 80),
        'ema_speed_period': (5, 60),
        'zscore_period': (50, 300),
        'zscore_threshold': (1.0, 5.0),
        'atr_period': (5, 30),
        'atr_multiplier_sl': (0.5, 6.0),
        'atr_multiplier_tp': (2.0, 25.0), # Expanded for massive ROI potential
        'use_taker_filter': [True, False],
        'taker_threshold': (0.5, 0.7)
    }
