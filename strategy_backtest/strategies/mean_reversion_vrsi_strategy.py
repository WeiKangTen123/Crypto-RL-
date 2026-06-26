"""
Volume-Weighted Mean Reversion (V-RSI)
=======================================
Core Hypothesis:
  Standard RSI ignores volume. V-RSI weights price moves by volume, so an
  extreme reading means MASSIVE volume has driven a one-sided move — likely
  leading to liquidity exhaustion and a snap-back to VWAP.

Entry:
  LONG  : V-RSI < vrsi_oversold  AND close < VWAP - vwap_std_mult * VWAP_std
  SHORT : V-RSI > vrsi_overbought AND close > VWAP + vwap_std_mult * VWAP_std
  Edge detection: fires only on the FIRST bar the condition turns true.

Exit (first to trigger):
  1. Stop Loss     : price moves sl_pct against entry (checked via Low/High)
  2. Trend trap    : V-RSI stays at deep extreme (<10 or >90) for 3+ bars → not a reversion
  3. Take Profit   : close returns to VWAP
  4. V-RSI reset   : V-RSI crosses back above/below 50

Timeframe: 5m or 15m (scalp/day trade)
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy


class MeanReversionVRSI(BaseStrategy):
    
    OPTIMIZATION_RANGES = {
    'vrsi_period': (10, 80),
    'vrsi_oversold': (5.0, 25.0),    # Force extreme panic
    'vrsi_overbought': (75.0, 95.0), # Force extreme mania
    'vwap_period': (50, 400),
    'vwap_std_mult': (3.0, 6.0),     # Massive deviation required
    'sl_pct': (0.02, 0.15),          # Wider stop for violent markets
    'extreme_bars': (1, 15),
    'exit_mode': ['VWAP_REVERT', 'VRSI_RESET', 'DYNAMIC_TRAILING'],
    'entry_filter': ['NONE', 'TREND_EMA', 'VOL_SPIKE', 'ADX_BLOCKER'],
    'max_hold_bars': (10, 100),      # Allow up to ~8 hours to revert
    'consecutive_signals': (1, 6),
    'adx_period': (10, 40),
    'adx_threshold': (20, 50),
    'min_hold_bars': (0, 15)
}

    SIGNAL_PARAMS = frozenset([
        'vrsi_period', 'vrsi_oversold', 'vrsi_overbought',
        'vwap_period', 'vwap_std_mult', 'ema_period', 'use_trend_filter',
        'sl_pct', 'extreme_bars', 'exit_mode', 'entry_filter', 
        'max_hold_bars', 'consecutive_signals', 'adx_period', 'adx_threshold'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        vrsi_period: int = 71,
        vrsi_oversold: float = 8.1484,
        vrsi_overbought: float = 79.9282,
        vwap_period: int = 400,
        vwap_std_mult: float = 5.8187,
        sl_pct: float = 0.0255,          # 0.4% hard stop
        vrsi_extreme_low: float = 10.0,  # V-RSI below this = trending down, not reverting
        vrsi_extreme_high: float = 90.0,
        extreme_bars: int = 3,
        ema_period: int = 67,
        use_trend_filter: bool = False,
        exit_mode: str = 'DYNAMIC_TRAILING',
        entry_filter: str = 'VOL_SPIKE',
        max_hold_bars: int = 90,         # Force close if not reverting fast enough
        consecutive_signals: int = 1,    # Require N consecutive bars of signal
        adx_period: int = 20,
        adx_threshold: float = 27.0,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.vrsi_period = vrsi_period
        self.vrsi_oversold = vrsi_oversold
        self.vrsi_overbought = vrsi_overbought
        self.vwap_period = vwap_period
        self.vwap_std_mult = vwap_std_mult
        self.sl_pct = sl_pct
        self.vrsi_extreme_low = vrsi_extreme_low
        self.vrsi_extreme_high = vrsi_extreme_high
        self.extreme_bars = extreme_bars
        self.ema_period = ema_period
        self.use_trend_filter = use_trend_filter
        self.exit_mode = exit_mode
        self.entry_filter = entry_filter
        self.max_hold_bars = max_hold_bars
        self.consecutive_signals = consecutive_signals
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

        self._s = {
            1:  dict(entry_price=None, sl_price=None, ts_price=None, extreme_count=0, bars_held=0),
            -1: dict(entry_price=None, sl_price=None, ts_price=None, extreme_count=0, bars_held=0),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close  = df['Close']
        volume = df['Volume']

        # 1. V-RSI
        price_chg = close.diff()
        U = volume * price_chg.clip(lower=0)
        D = volume * (-price_chg).clip(lower=0)

        sma_u = U.rolling(window=self.vrsi_period, min_periods=self.vrsi_period).mean()
        sma_d = D.rolling(window=self.vrsi_period, min_periods=self.vrsi_period).mean()

        rs = sma_u / (sma_d + 1e-10)
        df['vrsi'] = 100.0 - (100.0 / (1.0 + rs))

        # 2. Rolling VWAP and std bands (std measured as deviation of typical from VWAP)
        typical = (df['High'] + df['Low'] + df['Close']) / 3.0
        rolling_tp_vol = (typical * volume).rolling(window=self.vwap_period).sum()
        rolling_vol    = volume.rolling(window=self.vwap_period).sum()
        df['vwap']     = rolling_tp_vol / (rolling_vol + 1e-10)
        df['vwap_std'] = (typical - df['vwap']).rolling(window=self.vwap_period).std()
        df['vwap_upper'] = df['vwap'] + self.vwap_std_mult * df['vwap_std']
        df['vwap_lower'] = df['vwap'] - self.vwap_std_mult * df['vwap_std']

        # 3. Entry Filter Switch
        long_ok  = (df['vrsi'] < self.vrsi_oversold)   & (close < df['vwap_lower'])
        short_ok = (df['vrsi'] > self.vrsi_overbought)  & (close > df['vwap_upper'])

        if self.entry_filter == 'TREND_EMA':
            import ta
            df['ema_trend'] = ta.trend.ema_indicator(close, window=self.ema_period)
            long_ok = long_ok & (close > df['ema_trend'])
            short_ok = short_ok & (close < df['ema_trend'])
        elif self.entry_filter == 'VOL_SPIKE':
            vol_sma = volume.rolling(window=20).mean()
            vol_spike = volume > (vol_sma * 2.0)
            long_ok = long_ok & vol_spike
            short_ok = short_ok & vol_spike
        elif self.entry_filter == 'ADX_BLOCKER':
            import talib
            df['adx'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=self.adx_period)
            adx_ok = df['adx'] < self.adx_threshold  # Refuse entry in violent trend
            long_ok = long_ok & adx_ok
            short_ok = short_ok & adx_ok

        # 4. Entry conditions + Consecutive Signal Requirement
        if self.consecutive_signals > 1:
            long_ok = long_ok.rolling(window=self.consecutive_signals).sum() >= self.consecutive_signals
            short_ok = short_ok.rolling(window=self.consecutive_signals).sum() >= self.consecutive_signals

        signals = np.zeros(len(df), dtype=int)
        long_edge  = long_ok  & ~long_ok.shift(1).fillna(False)
        short_edge = short_ok & ~short_ok.shift(1).fillna(False)
        signals[long_edge.values]  = 1
        signals[short_edge.values] = -1

        df['signal'] = signals

        self._vrsi_arr = df['vrsi'].values
        self._vwap_arr = df['vwap'].values
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side      = int(np.sign(position))
        s         = self._s[side]
        bar_idx   = self._bar_index_map.get(row.name, -1)
        curr      = float(row['Close'])
        bar_low   = float(row['Low'])
        bar_high  = float(row['High'])

        # New trade — reset state
        if entry_price != s['entry_price']:
            sl = entry_price * (1.0 - side * self.sl_pct)
            s.update(entry_price=entry_price, sl_price=sl, ts_price=entry_price, extreme_count=0, bars_held=0)

        s['bars_held'] += 1
        
        # 0. Time-Bomb Exit (Max Hold Bars)
        if s['bars_held'] > self.max_hold_bars:
            return 'EXIT', curr

        vrsi = float(self._vrsi_arr[bar_idx]) if bar_idx >= 0 else 50.0
        vwap = float(self._vwap_arr[bar_idx]) if bar_idx >= 0 else curr

        # 2. Trend-trap exit: V-RSI deeper extreme for extreme_bars consecutive bars
        if side == 1 and vrsi < self.vrsi_extreme_low:
            s['extreme_count'] += 1
            if s['extreme_count'] >= self.extreme_bars:
                return 'EXIT', curr
        elif side == -1 and vrsi > self.vrsi_extreme_high:
            s['extreme_count'] += 1
            if s['extreme_count'] >= self.extreme_bars:
                return 'EXIT', curr
        else:
            s['extreme_count'] = 0

        # 3. SL vs exit with candle direction
        if side == 1:
            if self.exit_mode == 'DYNAMIC_TRAILING':
                dist_to_vwap = abs(curr - vwap)
                new_ts = curr - (dist_to_vwap * 0.5)
                s['ts_price'] = max(s['ts_price'], new_ts)
                if bar_low <= s['sl_price']: return 'SL', s['sl_price']
                if bar_low <= s['ts_price'] and curr > entry_price: return 'TS', s['ts_price']
            elif self.exit_mode == 'VWAP_REVERT':
                if bar_low <= s['sl_price']: return 'SL', s['sl_price']
                if curr >= vwap and curr > entry_price: return 'TP', vwap
            elif self.exit_mode == 'VRSI_RESET':
                if bar_low <= s['sl_price']: return 'SL', s['sl_price']
                if vrsi > 50.0 and curr > entry_price: return 'TP', curr
        else:
            if self.exit_mode == 'DYNAMIC_TRAILING':
                dist_to_vwap = abs(curr - vwap)
                new_ts = curr + (dist_to_vwap * 0.5)
                s['ts_price'] = min(s['ts_price'], new_ts)
                if bar_high >= s['sl_price']: return 'SL', s['sl_price']
                if bar_high >= s['ts_price'] and curr < entry_price: return 'TS', s['ts_price']
            elif self.exit_mode == 'VWAP_REVERT':
                if bar_high >= s['sl_price']: return 'SL', s['sl_price']
                if curr <= vwap and curr < entry_price: return 'TP', vwap
            elif self.exit_mode == 'VRSI_RESET':
                if bar_high >= s['sl_price']: return 'SL', s['sl_price']
                if vrsi < 50.0 and curr < entry_price: return 'TP', curr

        return 'HOLD', None
