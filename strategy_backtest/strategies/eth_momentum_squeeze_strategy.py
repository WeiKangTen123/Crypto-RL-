import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_bollinger_bands, calc_keltner_channels

class ETHMomentumSqueezeStrategy(BaseStrategy):
    """
    ETH Momentum Bollinger Keltner Squeeze Strategy
    Identifies low-volatility squeezes (BB inside KC) and enters on momentum breakouts.
    """
    OPTIMIZATION_RANGES = {
        'bb_period': (10, 40),
        'bb_std': (1.5, 3.0),
        'kc_period': (10, 40),
        'kc_mult': (1.0, 2.5),
        'ema_trend_period': (50, 300),
        'atr_period': (5, 20),
        'atr_multiplier_sl': (0.5, 3.0),
        'atr_multiplier_tp': (2.0, 10.0),
        'direction': ['both', 'long_only', 'short_only']
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.bb_period = int(kwargs.get('bb_period', 20))
        self.bb_std = float(kwargs.get('bb_std', 2.0))
        self.kc_period = int(kwargs.get('kc_period', 20))
        self.kc_mult = float(kwargs.get('kc_mult', 1.5))
        self.ema_trend_period = int(kwargs.get('ema_trend_period', 200))
        self.atr_period = int(kwargs.get('atr_period', 14))
        self.atr_multiplier_sl = float(kwargs.get('atr_multiplier_sl', 1.5))
        self.atr_multiplier_tp = float(kwargs.get('atr_multiplier_tp', 3.0))
        self.direction = str(kwargs.get('direction', 'both'))
        
        self._s = {
            1:  dict(entry_price=None, sl=None, tp=None),
            -1: dict(entry_price=None, sl=None, tp=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Bollinger Bands & Keltner Channels
        df['BBU_20_2.0'], _, df['BBL_20_2.0'] = calc_bollinger_bands(df, self.bb_period, self.bb_std)
        df['KCU_20_1.5'], _, df['KCL_20_1.5'] = calc_keltner_channels(df, self.kc_period, self.kc_mult)
        
        # 2. Squeeze Condition (BB completely inside KC)
        df['sqz_on'] = (df['BBL_20_2.0'] > df['KCL_20_1.5']) & (df['BBU_20_2.0'] < df['KCU_20_1.5'])
        df['sqz_off'] = ~df['sqz_on']
        
        # 3. Indicators
        df['ema_trend'] = talib.EMA(df['Close'], timeperiod=self.ema_trend_period)
        df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.atr_period)
        
        df.fillna(0, inplace=True)
        
        # 4. Squeeze Firing (Squeeze was ON, now OFF)
        sqz_firing = df['sqz_on'].shift(1) & df['sqz_off']
        
        # 5. Conditions
        long_cond = sqz_firing & (df['Close'] > df['BBU_20_2.0']) & (df['macdhist'] > 0) & (df['Close'] > df['ema_trend'])
        short_cond = sqz_firing & (df['Close'] < df['BBL_20_2.0']) & (df['macdhist'] < 0) & (df['Close'] < df['ema_trend'])

        signals = np.zeros(len(df), dtype=int)
        
        if self.direction in ['both', 'long_only']:
            long_edge = long_cond & ~long_cond.shift(1).fillna(False)
            signals[long_edge.values] = 1
            
        if self.direction in ['both', 'short_only']:
            short_edge = short_cond & ~short_cond.shift(1).fillna(False)
            signals[short_edge.values] = -1

        df['signal'] = signals
        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s = self._s[side]

        if entry_price != s['entry_price']:
            s['entry_price'] = entry_price
            atr = float(row['atr'])
            if side == 1:
                s['sl'] = entry_price - (self.atr_multiplier_sl * atr)
                s['tp'] = entry_price + (self.atr_multiplier_tp * atr)
            else:
                s['sl'] = entry_price + (self.atr_multiplier_sl * atr)
                s['tp'] = entry_price - (self.atr_multiplier_tp * atr)

        if side == 1:
            if float(row['Low'])  <= s['sl']: return 'SL', s['sl']

            if float(row['High']) >= s['tp']: return 'TP', s['tp']
        else:
            if float(row['High']) >= s['sl']: return 'SL', s['sl']

            if float(row['Low'])  <= s['tp']: return 'TP', s['tp']

        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        if params.get('atr_multiplier_tp', 0) <= params.get('atr_multiplier_sl', 0):
            return False
        return True
