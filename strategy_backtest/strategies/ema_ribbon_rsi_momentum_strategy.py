import numpy as np
import pandas as pd
import talib
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_ema_ribbon, calc_rsi, calc_atr


class EMARibbonRSIMomentumStrategy(BaseStrategy):
    """
    EMA Ribbon Alignment + RSI Momentum Strategy.

    Factor Card: factor_library/Trend_Momentum/20260527_ema_ribbon_rsi_momentum.md
    Source: TradingView (Popular Setup)
    Registered IDs: 186 (BTC/4h), 187 (ETH/4h), 188 (SOL/4h)

    Logic:
      - Long:  EMA_fast > EMA_med > EMA_slow AND RSI > rsi_threshold.
      - Short: EMA_fast < EMA_med < EMA_slow AND RSI < (100 - rsi_threshold).
      - Entry trigger: first bar of full ribbon alignment (crossover-style entry).
      - Exit: EMA fast crosses back over EMA med, OR ATR SL/TP.
    """

    SIGNAL_PARAMS = frozenset([
        'ema_fast', 'ema_med', 'ema_slow', 'rsi_period', 'rsi_threshold',
        'require_crossover', 'exit_mode',
    ])

    OPTIMIZATION_RANGES = {
        # Logic switches
        'exit_mode':        ['FIXED_RR', 'TRAILING_STOP'],
        'require_crossover': [True, False],   # True = only first bar of alignment (default); False = all aligned bars
        # Indicator tuning
        'ema_fast':         (5, 20),
        'ema_med':          (15, 40),
        'ema_slow':         (30, 100),
        'rsi_period':       (7, 28),
        'rsi_threshold':    (45.0, 60.0),
        # Risk
        'atr_period':       (7, 28),
        'sl_atr_mult':      (0.5, 3.0),
        'tp_rr':            (1.5, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        ema_fast: int = 9,
        ema_med: int = 21,
        ema_slow: int = 55,
        rsi_period: int = 14,
        rsi_threshold: float = 50.0,
        atr_period: int = 14,
        sl_atr_mult: float = 2.0,
        tp_rr: float = 2.0,
        exit_mode: str = 'FIXED_RR',
        require_crossover: bool = True,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.ema_fast         = int(ema_fast)
        self.ema_med          = int(ema_med)
        self.ema_slow         = int(ema_slow)
        self.rsi_period       = int(rsi_period)
        self.rsi_threshold    = float(rsi_threshold)
        self.atr_period       = int(atr_period)
        self.sl_atr_mult      = float(sl_atr_mult)
        self.tp_rr            = float(tp_rr)
        self.exit_mode        = exit_mode
        self.require_crossover = bool(require_crossover)

        # State dict — track entry_price to detect new trades and reset targets
        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
        }

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """Enforce EMA period ordering: fast < med < slow."""
        return (
            params.get('ema_fast', 9) < params.get('ema_med', 21) < params.get('ema_slow', 55)
        )

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close = df['Close']

        # 1. EMA Ribbon — from library (Library First mandate)
        ribbon = calc_ema_ribbon(df, periods=(self.ema_fast, self.ema_med, self.ema_slow))
        df['ema_f'] = ribbon[self.ema_fast]
        df['ema_m'] = ribbon[self.ema_med]
        df['ema_s'] = ribbon[self.ema_slow]

        # 2. RSI — from library
        df['rsi'] = calc_rsi(close, self.rsi_period)

        # 3. ATR for risk management
        df['atr'] = calc_atr(df, self.atr_period)

        # 4. Ribbon alignment (regime guard as inline boolean mask)
        long_aligned  = (df['ema_f'] > df['ema_m']) & (df['ema_m'] > df['ema_s']) & (df['rsi'] > self.rsi_threshold)
        short_aligned = (df['ema_f'] < df['ema_m']) & (df['ema_m'] < df['ema_s']) & (df['rsi'] < (100.0 - self.rsi_threshold))

        df['signal'] = 0

        if self.require_crossover:
            # Only enter on the FIRST bar of alignment (crossover-style, avoids late entry)
            df.loc[long_aligned  & (~long_aligned.shift(1, fill_value=False)),  'signal'] = 1
            df.loc[short_aligned & (~short_aligned.shift(1, fill_value=False)), 'signal'] = -1
        else:
            # Enter on every aligned bar (generates more trades)
            df.loc[long_aligned,  'signal'] = 1
            df.loc[short_aligned, 'signal'] = -1

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
        atr  = float(row['atr']) if float(row['atr']) > 0 else entry_price * 0.01

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

            # Signal exit: fast EMA crosses back over medium EMA
            ema_f = float(row['ema_f'])
            ema_m = float(row['ema_m'])
            if side == 1 and ema_f < ema_m:
                return 'EXIT', None
            if side == -1 and ema_f > ema_m:
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
