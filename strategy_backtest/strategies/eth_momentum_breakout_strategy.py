import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
import strategy_backtest.library as sl

class ETHMomentumBreakoutStrategy(BaseStrategy):
    """
    ETH Momentum Breakout Strategy
    ==========================
    Category: Volatility-Breakout
    Logic:
    1. Squeeze detection using BB inside KC (from library).
    2. Entry on breakout of BB with volume and RSI confirmation.
    3. Logic switches for entry filters and exit methodology.
    """

    OPTIMIZATION_RANGES = {
        'bb_period': (15, 45),
        'bb_std': (1.5, 3.5),
        'tp_rr': (2.0, 15.0),
        'squeeze_duration': [3, 5, 8],
        'entry_confirmation': ['VOLUME_SPIKE', 'RSI_FILTER', 'BOTH'],
        'exit_mode': ['FIXED_RR', 'ATR_TRAILING_STOP'],
    }

    SIGNAL_PARAMS = frozenset({
        'bb_period', 'bb_std', 'kc_period', 'kc_mult',
        'rsi_period', 'atr_period', 'tp_rr',
        'squeeze_duration', 'entry_confirmation', 'exit_mode'
    })

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 45,
        bb_std: float = 2.2327,
        kc_period: int = 20,
        kc_mult: float = 1.5,
        rsi_period: int = 13,
        atr_period: int = 8,
        tp_rr: float = 2.2541,
        squeeze_duration: int = 3,
        entry_confirmation: str = 'VOLUME_SPIKE',
        exit_mode: str = 'FIXED_RR',
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.kc_period = kc_period
        self.kc_mult = kc_mult
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.tp_rr = tp_rr
        self.squeeze_duration = squeeze_duration
        self.entry_confirmation = entry_confirmation
        self.exit_mode = exit_mode

        self._s = {
            1:  dict(entry_price=None, sl_price=None, ts_price=None, bars_held=0),
            -1: dict(entry_price=None, sl_price=None, ts_price=None, bars_held=0),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        close = df['Close']
        
        # 1. Squeeze Detection
        df['squeeze'] = sl.calc_bb_kc_squeeze(
            df,
            bb_period=self.bb_period,
            bb_std=self.bb_std,
            kc_period=self.kc_period,
            kc_mult=self.kc_mult
        )
        df['squeeze_count'] = df['squeeze'].astype(int).rolling(window=self.squeeze_duration).sum()
        df['was_squeezed'] = df['squeeze_count'] >= self.squeeze_duration

        # 2. Indicators
        upper_bb, mid_bb, lower_bb = talib.BBANDS(close, timeperiod=self.bb_period, nbdevup=self.bb_std)
        df['rsi'] = talib.RSI(close, timeperiod=self.rsi_period)
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.atr_period)
        df['vol_sma'] = df['Volume'].rolling(window=20).mean()

        df['base_cloud_top'] = upper_bb # For exit logic reuse if needed
        df['base_cloud_bottom'] = lower_bb

        # 3. Signals
        long_base = (df['was_squeezed'].shift(1)) & (close > upper_bb)
        short_base = (df['was_squeezed'].shift(1)) & (close < lower_bb)

        # Confirmations
        vol_ok = df['Volume'] > (df['vol_sma'] * 1.8) # Updated from 1.5 to 1.8
        rsi_long_ok = df['rsi'] < 75 # Updated from 80 to 75
        rsi_short_ok = df['rsi'] > 25 # Updated from 20 to 25

        if self.entry_confirmation == 'VOLUME_SPIKE':
            long_ok = long_base & vol_ok
            short_ok = short_base & vol_ok
        elif self.entry_confirmation == 'RSI_FILTER':
            long_ok = long_base & rsi_long_ok
            short_ok = short_base & rsi_short_ok
        elif self.entry_confirmation == 'BOTH':
            long_ok = long_base & vol_ok & rsi_long_ok
            short_ok = short_base & vol_ok & rsi_short_ok
        else: # Default or unforeseen case, no extra confirmation
            long_ok = long_base
            short_ok = short_base

        signals = np.zeros(len(df), dtype=int)
        signals[long_ok] = 1
        signals[short_ok] = -1
        df['signal'] = signals
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0: return 'HOLD', None
        side = int(np.sign(position))
        s = self._s[side]
        curr = float(row['Close'])
        atr = float(row['atr'])

        if entry_price != s['entry_price']:
            sl = entry_price - side * (atr * 2.0)
            tp = entry_price + side * (abs(entry_price - sl) * self.tp_rr)
            s.update(entry_price=entry_price, sl_price=sl, tp_price=tp, ts_price=sl, bars_held=0)

        s['bars_held'] += 1

        if side == 1:
            if row['Low'] <= s['sl_price']: return 'SL', s['sl_price']
            if self.exit_mode == 'FIXED_RR' and row['High'] >= s['tp_price']:
                return 'TP', s['tp_price']
            if self.exit_mode == 'ATR_TRAILING_STOP':
                new_ts = curr - (atr * 2.0)
                s['ts_price'] = max(s['ts_price'], new_ts)
                if row['Low'] <= s['ts_price']: return 'TS', s['ts_price']
        else:
            if row['High'] >= s['sl_price']: return 'SL', s['sl_price']
            if self.exit_mode == 'FIXED_RR' and row['Low'] <= s['tp_price']:
                return 'TP', s['tp_price']
            if self.exit_mode == 'ATR_TRAILING_STOP':
                new_ts = curr + (atr * 2.0)
                s['ts_price'] = min(s['ts_price'], new_ts)
                if row['High'] >= s['ts_price']: return 'TS', s['ts_price']

        return 'HOLD', None
