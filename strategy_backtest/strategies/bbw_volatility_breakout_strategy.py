import numpy as np
import pandas as pd
import talib
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_bbw, calc_atr


class BBWVolatilityBreakoutStrategy(BaseStrategy):
    """
    Bollinger Band Width Volatility Breakout Strategy.

    Factor Card: factor_library/Volatility_Breakout/20260527_bbw_volatility_breakout.md
    Source: GitHub (Quantitative breakout strategies)
    Registered IDs: 184 (BTC/4h), 185 (SOL/4h)

    Logic:
      - Volatility squeeze: BBW < its own N-period SMA (consolidation).
      - Long breakout:  Close > Upper BB AND previous bar was in squeeze AND Volume > Vol_SMA.
      - Short breakout: Close < Lower BB AND previous bar was in squeeze AND Volume > Vol_SMA.
      - Exit: ATR SL/TP or price crosses back through BB middle band.
    """

    SIGNAL_PARAMS = frozenset([
        'bb_period', 'bb_std', 'bbw_sma_period', 'vol_sma_period',
        'use_volume_filter', 'exit_mode',
    ])

    OPTIMIZATION_RANGES = {
        # Logic switches
        'exit_mode':         ['FIXED_RR', 'TRAILING_STOP'],
        'use_volume_filter': [True, False],
        # Indicator tuning
        'bb_period':         (10, 40),
        'bb_std':            (1.5, 3.0),
        'bbw_sma_period':    (10, 50),
        'vol_sma_period':    (10, 50),
        # Risk
        'atr_period':        (7, 28),
        'sl_atr_mult':       (0.5, 3.0),
        'tp_rr':             (1.5, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bbw_sma_period: int = 20,
        vol_sma_period: int = 20,
        atr_period: int = 14,
        sl_atr_mult: float = 2.0,
        tp_rr: float = 2.0,
        exit_mode: str = 'FIXED_RR',
        use_volume_filter: bool = True,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.bb_period         = int(bb_period)
        self.bb_std            = float(bb_std)
        self.bbw_sma_period    = int(bbw_sma_period)
        self.vol_sma_period    = int(vol_sma_period)
        self.atr_period        = int(atr_period)
        self.sl_atr_mult       = float(sl_atr_mult)
        self.tp_rr             = float(tp_rr)
        self.exit_mode         = exit_mode
        self.use_volume_filter = bool(use_volume_filter)

        # State dict — track entry_price to detect new trades and reset targets
        self._s = {
            1:  dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
            -1: dict(entry_price=None, sl_price=None, tp_price=None, ts_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        close = df['Close']

        # 1. Bollinger Bands via library
        upper, mid, lower = talib.BBANDS(
            close, timeperiod=self.bb_period,
            nbdevup=self.bb_std, nbdevdn=self.bb_std,
        )
        df['BBU'] = upper
        df['BBM'] = mid
        df['BBL'] = lower

        # 2. BBW from library (Library First mandate)
        df['BBW'] = calc_bbw(df, self.bb_period, self.bb_std)

        # 3. BBW squeeze: BBW below its own rolling mean
        df['BBW_SMA'] = df['BBW'].rolling(window=self.bbw_sma_period).mean()

        # 4. Volume filter
        df['Vol_SMA'] = df['Volume'].rolling(window=self.vol_sma_period).mean()

        # 5. ATR for risk management
        df['atr'] = calc_atr(df, self.atr_period)

        # 6. Regime guard (squeeze must have occurred on prior bar to avoid lookahead)
        prev_squeeze = (df['BBW'] < df['BBW_SMA']).shift(1, fill_value=False)

        # Volume confirmation (logic switch)
        if self.use_volume_filter:
            vol_ok = df['Volume'] > df['Vol_SMA']
        else:
            vol_ok = True

        # 7. Breakout signals
        long_cond  = (close > df['BBU']) & prev_squeeze & vol_ok
        short_cond = (close < df['BBL']) & prev_squeeze & vol_ok

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

            # Signal exit: price crosses back through middle band
            bbm = float(row['BBM'])
            if side == 1 and float(row['Close']) < bbm:
                return 'EXIT', None
            if side == -1 and float(row['Close']) > bbm:
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
