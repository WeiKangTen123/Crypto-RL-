import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_trend_intensity_index, calc_atr


class TrendIntensityIndexStrategy(BaseStrategy):
    """
    Trend Intensity Index (TII) Strategy.

    Factor Card: factor_library/Trend_Momentum/20260527_trend_intensity_index_tii.md
    Source: M.H. Pee / TradingPedia
    Registered IDs: 182 (BTC/4h), 183 (ETH/4h)

    Logic:
      - TII (major_period, minor_period): Measures % of positive deviations from SMA.
      - Long entry:  TII crosses above tii_upper (default 80) AND price > SMA-200.
      - Short entry: TII crosses below tii_lower (default 20) AND price < SMA-200.
      - Exit:        ATR-based SL/TP or when TII crosses back through 50.
    """

    SIGNAL_PARAMS = frozenset([
        'major_period', 'minor_period', 'tii_upper', 'tii_lower',
        'sma_macro_period', 'use_sma_filter', 'exit_mode',
    ])

    OPTIMIZATION_RANGES = {
        # Logic switches
        'exit_mode':        ['FIXED_RR', 'TRAILING_STOP'],
        'use_sma_filter':   [True, False],
        # Indicator tuning
        'major_period':     (30, 100),
        'minor_period':     (10, 60),
        'tii_upper':        (70.0, 90.0),
        'tii_lower':        (10.0, 30.0),
        'sma_macro_period': (100, 300),
        # Risk
        'atr_period':       (7, 28),
        'sl_atr_mult':      (0.5, 3.0),
        'tp_rr':            (1.5, 5.0),
    }

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
        exit_mode: str = 'FIXED_RR',
        use_sma_filter: bool = True,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.major_period     = int(major_period)
        self.minor_period     = int(minor_period)
        self.tii_upper        = float(tii_upper)
        self.tii_lower        = float(tii_lower)
        self.sma_macro_period = int(sma_macro_period)
        self.atr_period       = int(atr_period)
        self.tp_rr            = float(tp_rr)
        self.sl_atr_mult      = float(sl_atr_mult)
        self.exit_mode        = exit_mode
        self.use_sma_filter   = bool(use_sma_filter)

        # State dict — track entry_price to detect new trades and reset targets
        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
        }

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        return params.get('major_period', 60) > params.get('minor_period', 30)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close = df['Close']

        # 1. TII — from library (Library First mandate)
        df['tii'] = calc_trend_intensity_index(close, self.major_period, self.minor_period)

        # 2. SMA-200 macro regime filter
        df['sma_200'] = talib.SMA(close, timeperiod=self.sma_macro_period)

        # 3. ATR for risk management
        df['atr'] = calc_atr(df, self.atr_period)

        # 4. Signal logic: TII crossover above/below thresholds
        tii_cross_up   = (df['tii'] > self.tii_upper) & (df['tii'].shift(1) <= self.tii_upper)
        tii_cross_down = (df['tii'] < self.tii_lower) & (df['tii'].shift(1) >= self.tii_lower)

        # 5. Regime guard (inline boolean mask per BaseStrategy contract)
        if self.use_sma_filter:
            regime_up   = close > df['sma_200']
            regime_down = close < df['sma_200']
        else:
            regime_up   = True
            regime_down = True

        long_cond  = tii_cross_up   & regime_up
        short_cond = tii_cross_down & regime_down

        df['signal'] = 0
        df.loc[long_cond,  'signal'] = 1
        df.loc[short_cond, 'signal'] = -1

        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s    = self._s[side]
        atr  = float(row['atr']) if row['atr'] > 0 else entry_price * 0.01

        # ── Reset state when a NEW trade starts ──────────────────────────────
        if s['entry_price'] != entry_price:
            sl = entry_price - side * (self.sl_atr_mult * atr)
            tp = entry_price + side * (abs(entry_price - sl) * self.tp_rr)
            s.update(entry_price=entry_price, sl_price=sl, tp_price=tp, ts_price=sl)

        # ── Hard stop-loss (always first) ────────────────────────────────────
        if (side ==  1 and float(row['Low'])  <= s['sl_price']) or \
           (side == -1 and float(row['High']) >= s['sl_price']):
            return 'SL', s['sl_price']

        # ── Exit mode switch ─────────────────────────────────────────────────
        if self.exit_mode == 'FIXED_RR':
            if (side ==  1 and float(row['High']) >= s['tp_price']) or \
               (side == -1 and float(row['Low'])  <= s['tp_price']):
                return 'TP', s['tp_price']

            # Signal exit: TII crosses back through midpoint
            tii = float(row['tii'])
            if (side == 1 and tii < 50) or (side == -1 and tii > 50):
                return 'EXIT', None

        else:  # TRAILING_STOP
            if side == 1:
                s['ts_price'] = max(s['ts_price'], float(row['Close']) - self.sl_atr_mult * atr)
                if float(row['Low']) <= s['ts_price']:
                    return 'TS', s['ts_price']
            else:
                s['ts_price'] = min(s['ts_price'], float(row['Close']) + self.sl_atr_mult * atr)
                if float(row['High']) >= s['ts_price']:
                    return 'TS', s['ts_price']

        return 'HOLD', None
