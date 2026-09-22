import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class TakerBuyIntensityMomentumStrategy(BaseStrategy):
    """
    Taker Buy Intensity Momentum Strategy
    Uses Order Flow (taker_buy_base_vol) to find aggressive market buys/sells.
    """
    OPTIMIZATION_RANGES = {
        'taker_ratio_threshold': (0.51, 0.70),
        'vol_ma_period': (10, 50),
        'trend_ema_period': (10, 100),
        'atr_period': (5, 20),
        'atr_multiplier_tp': (1.5, 10.0),
        'atr_multiplier_sl': (0.5, 3.0),
        'exit_mode': ['ATR_ONLY', 'NEUTRAL_RATIO_EXIT']
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.taker_ratio_threshold = float(kwargs.get('taker_ratio_threshold', 0.55))
        self.vol_ma_period = int(kwargs.get('vol_ma_period', 20))
        self.trend_ema_period = int(kwargs.get('trend_ema_period', 20))
        self.atr_period = int(kwargs.get('atr_period', 14))
        self.atr_multiplier_tp = float(kwargs.get('atr_multiplier_tp', 3.0))
        self.atr_multiplier_sl = float(kwargs.get('atr_multiplier_sl', 1.5))
        self.exit_mode = str(kwargs.get('exit_mode', 'ATR_ONLY'))
        
        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # Base indicators
        df['vol_sma'] = df['Volume'].rolling(window=self.vol_ma_period).mean()
        df['trend_ema'] = talib.EMA(df['Close'], timeperiod=self.trend_ema_period)
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.atr_period)
        
        # Order flow ratio
        df['taker_buy_ratio'] = 0.5
        if 'taker_buy_base_asset_volume' in df.columns:
            df['taker_buy_ratio'] = df['taker_buy_base_asset_volume'] / (df['Volume'] + 1e-10)
        elif 'taker_buy_base_vol' in df.columns:
            df['taker_buy_ratio'] = df['taker_buy_base_vol'] / (df['Volume'] + 1e-10)

        df.fillna(0, inplace=True)

        # Conditions
        vol_spike = df['Volume'] > df['vol_sma']
        
        long_ok = (df['taker_buy_ratio'] > self.taker_ratio_threshold) & vol_spike & (df['Close'] > df['trend_ema'])
        short_ok = (df['taker_buy_ratio'] < (1.0 - self.taker_ratio_threshold)) & vol_spike & (df['Close'] < df['trend_ema'])

        signals = np.zeros(len(df), dtype=int)
        long_edge = long_ok & ~long_ok.shift(1, fill_value=False)
        short_edge = short_ok & ~short_ok.shift(1, fill_value=False)
        
        signals[long_edge.values] = 1
        signals[short_edge.values] = -1

        df['signal'] = signals
        
        self._taker_arr = df['taker_buy_ratio'].values
        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s = self._s[side]
        curr = float(row['Close'])
        bar_idx = self._bar_index_map.get(row.name, -1)

        # New trade logic
        if entry_price != s['entry_price']:
            s['entry_price'] = entry_price
            atr = float(row['atr'])
            if side == 1:
                s['sl_price'] = entry_price - (self.atr_multiplier_sl * atr)
                s['tp_price'] = entry_price + (self.atr_multiplier_tp * atr)
            else:
                s['sl_price'] = entry_price + (self.atr_multiplier_sl * atr)
                s['tp_price'] = entry_price - (self.atr_multiplier_tp * atr)

        # 1. Hard SL/TP with candle direction
        if side == 1:
            if float(row['Low'])  <= s['sl_price']: return 'SL', s['sl_price']

            if float(row['High']) >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']

            if float(row['Low'])  <= s['tp_price']: return 'TP', s['tp_price']

        # 2. Dynamic Exit
        if self.exit_mode == 'NEUTRAL_RATIO_EXIT' and bar_idx >= 0:
            tr = float(self._taker_arr[bar_idx])
            if side == 1 and tr < 0.50:
                return 'EXIT', curr
            if side == -1 and tr > 0.50:
                return 'EXIT', curr

        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        if params.get('atr_multiplier_tp', 0) <= params.get('atr_multiplier_sl', 0) * 1.0:
            return False
        return True
