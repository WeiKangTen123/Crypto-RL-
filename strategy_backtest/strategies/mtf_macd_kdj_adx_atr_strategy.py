"""
Multi-Timeframe MACD + KDJ + ADX + ATR Strategy
==============================================================================
This strategy uses 1-hour granularity for entry signals but filters them using
higher timeframe (4-hour) trend and strength indicators.

Logic:
1. Entry (1h chart):
   - MACD Cross (1h) + KDJ Cross (1h) within window.
   - AND ADX (1h) > 20 (local momentum).
2. Filter (4h chart - simulated via resampling):
   - LONG only if Price > EMA200 (4h) AND ADX(4h) > 25.
   - SHORT only if Price < EMA200 (4h) AND ADX(4h) > 25.
3. Exit:
   - ATR-based Trailing Stop Loss.
   - ATR-based Take Profit.
   - KDJ reverse cross (1h).
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy

class MTF_MACDKDJ_ADX_ATR_Strategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'macd_fast', 'macd_slow', 'macd_signal',
        'kdj_period', 'kdj_oversold', 'kdj_overbought',
        'entry_window', 'adx_threshold_1h', 'adx_threshold_4h', 'ema_trend_4h'
    })

    OPTIMIZATION_RANGES = {
        'exit_mode':   ['FIXED_RR', 'TRAILING_STOP', 'KDJ_CROSS_ONLY'],
        'atr_multiplier_tp': (1.5, 10.0),
        'atr_multiplier_sl': (0.5, 4.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        macd_fast: int = 5,
        macd_slow: int = 63,
        macd_signal: int = 19,
        kdj_period: int = 25,
        kdj_oversold: float = 12.0,
        kdj_overbought: float = 76.0,
        entry_window: int = 19,
        adx_threshold_1h: float = 17.4943,
        adx_threshold_4h: float = 18.5091,
        ema_trend_4h: int = 97,
        atr_multiplier_sl: float = 0.5639,
        atr_multiplier_tp: float = 5.6043,
        exit_mode: str = 'FIXED_RR',
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.kdj_period = kdj_period
        self.kdj_oversold = kdj_oversold
        self.kdj_overbought = kdj_overbought
        self.entry_window = entry_window
        self.adx_threshold_1h = adx_threshold_1h
        self.adx_threshold_4h = adx_threshold_4h
        self.ema_trend_4h = ema_trend_4h
        self.atr_multiplier_sl = atr_multiplier_sl
        self.atr_multiplier_tp = atr_multiplier_tp
        self.exit_mode = exit_mode
        
        self._s = {
            1:  dict(count=0, entry_price=None, sl_price=None, tp_price=None, ts_price=None),
            -1: dict(count=0, entry_price=None, sl_price=None, tp_price=None, ts_price=None),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        
        # 1. 1h Indicators
        # MACD
        ema_fast = df['Close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd_hist = (ema_fast - ema_slow) - (ema_fast - ema_slow).ewm(span=self.macd_signal, adjust=False).mean()
        macd_turn_pos = (macd_hist > 0) & (macd_hist.shift(1) <= 0)
        macd_turn_neg = (macd_hist < 0) & (macd_hist.shift(1) >= 0)

        # KDJ
        low_min = df['Low'].rolling(window=self.kdj_period).min()
        high_max = df['High'].rolling(window=self.kdj_period).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-8) * 100
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        kdj_golden = (K > D) & (K.shift(1) <= D.shift(1))
        kdj_death = (K < D) & (K.shift(1) >= D.shift(1))
        
        # ADX 1h
        adx_1h = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14).adx()
        
        # ATR 1h
        self._atr_arr = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=14).average_true_range().values

        # 2. 4h Indicators (Simulated via resampling)
        df_4h = df.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
        ema_4h = df_4h['Close'].ewm(span=self.ema_trend_4h, adjust=False).mean()
        adx_4h = ta.trend.ADXIndicator(df_4h['High'], df_4h['Low'], df_4h['Close'], window=14).adx()
        
        # Realign to 1h
        ema_4h_1h = ema_4h.reindex(df.index, method='ffill')
        adx_4h_1h = adx_4h.reindex(df.index, method='ffill')
        
        # 3. Signals
        w = self.entry_window
        def _in_window(series):
            return series.astype(int).rolling(w, min_periods=1).max().fillna(0).astype(bool)

        long_ok = (
            _in_window(K < self.kdj_oversold) & _in_window(kdj_golden) & _in_window(macd_turn_pos)
            & (df['Close'] > ema_4h_1h) & (adx_4h_1h > self.adx_threshold_4h) & (adx_1h > self.adx_threshold_1h)
        )
        short_ok = (
            _in_window(K > self.kdj_overbought) & _in_window(kdj_death) & _in_window(macd_turn_neg)
            & (df['Close'] < ema_4h_1h) & (adx_4h_1h > self.adx_threshold_4h) & (adx_1h > self.adx_threshold_1h)
        )

        signals = np.zeros(len(df), dtype=int)
        long_edge = long_ok & ~long_ok.shift(1, fill_value=False)
        short_edge = short_ok & ~short_ok.shift(1, fill_value=False)
        signals[long_edge.values] = 1
        signals[short_edge.values] = -1
        
        df['signal'] = signals
        self._kdj_death_arr = kdj_death.values
        self._kdj_golden_arr = kdj_golden.values
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0: return 'HOLD', None
        side = int(np.sign(position))
        s = self._s[side]
        bar_idx = self._bar_index_map.get(row.name, -1)
        
        if entry_price != s['entry_price']:
            atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0
            s.update(entry_price=entry_price, sl_price=entry_price - side * (self.atr_multiplier_sl * atr),
                     tp_price=entry_price + side * (self.atr_multiplier_tp * atr), count=0, ts_price=entry_price - side * (self.atr_multiplier_sl * atr))
        
        s['count'] += 1
        curr_atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0
        
        # Exit mode logic with candle direction for SL vs TP
        if self.exit_mode == 'FIXED_RR':
            if side == 1:
                if row['Low']  <= s['sl_price']: return 'SL', s['sl_price']

                if row['High'] >= s['tp_price']: return 'TP', s['tp_price']
                if self._kdj_death_arr[bar_idx]: return 'EXIT', None
            else:
                if row['High'] >= s['sl_price']: return 'SL', s['sl_price']

                if row['Low']  <= s['tp_price']: return 'TP', s['tp_price']
                if self._kdj_golden_arr[bar_idx]: return 'EXIT', None

        elif self.exit_mode == 'TRAILING_STOP':
            if side == 1:
                if row['Low'] <= s['sl_price']: return 'SL', s['sl_price']
                new_ts = float(row['High']) - (self.atr_multiplier_sl * curr_atr)
                if new_ts > s['ts_price']: s['ts_price'] = new_ts
                if float(row['Low']) <= s['ts_price']: return 'TS', s['ts_price']
                if self._kdj_death_arr[bar_idx]: return 'EXIT', None
            else:
                if row['High'] >= s['sl_price']: return 'SL', s['sl_price']
                new_ts = float(row['Low']) + (self.atr_multiplier_sl * curr_atr)
                if new_ts < s['ts_price']: s['ts_price'] = new_ts
                if float(row['High']) >= s['ts_price']: return 'TS', s['ts_price']
                if self._kdj_golden_arr[bar_idx]: return 'EXIT', None

        elif self.exit_mode == 'KDJ_CROSS_ONLY':
            if (side == 1 and self._kdj_death_arr[bar_idx]) or (side == -1 and self._kdj_golden_arr[bar_idx]):
                return 'EXIT', None

        return 'HOLD', None
