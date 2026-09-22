import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_lorentzian_classification, calc_atr, calc_adx_dmi, calc_ema


class LorentzianClassificationMomentumStrategy(BaseStrategy):
    """
    Lorentzian KNN classification — votes k nearest historical bars using RSI/CCI/ADX
    features; enters when majority vote >= signal_threshold in chosen direction.

    Entry filters (entry_filter):
      ADX_ABOVE_20       — require ADX > adx_threshold for both long and short
      EMA_TREND_FILTER   — long only above EMA200, short only below EMA200
      NONE               — no filter

    Exit (exit_mode):
      ATR_TRAILING_STOP  — trail stop by sl_atr_mult × ATR from highest High / lowest Low
      CLASSIFICATION_FLIP — exit when score flips to opposite side threshold
    """

    SIGNAL_PARAMS = frozenset([
        'k_neighbors', 'history_window', 'rsi_period', 'cci_period', 'adx_period',
        'ema_period', 'adx_threshold', 'entry_filter', 'exit_mode',
        'signal_threshold', 'sl_atr_mult', 'atr_period',
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        k_neighbors: int = 5,
        history_window: int = 2000,
        rsi_period: int = 14,
        cci_period: int = 14,
        adx_period: int = 14,
        ema_period: int = 200,
        adx_threshold: int = 20,
        entry_filter: str = 'ADX_ABOVE_20',
        exit_mode: str = 'ATR_TRAILING_STOP',
        signal_threshold: int = 3,
        sl_atr_mult: float = 1.0,
        atr_period: int = 14,
        # legacy params accepted but unused
        tp_rr: float = 2.0,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.k_neighbors       = int(k_neighbors)
        self.history_window    = int(history_window)
        self.rsi_period        = int(rsi_period)
        self.cci_period        = int(cci_period)
        self.adx_period        = int(adx_period)
        self.ema_period        = int(ema_period)
        self.adx_threshold     = float(adx_threshold)
        self.entry_filter      = str(entry_filter)
        self.exit_mode         = str(exit_mode)
        self.signal_threshold  = int(signal_threshold)
        self.sl_atr_mult       = float(sl_atr_mult)
        self.atr_period        = int(atr_period)

        self._trail = {1: None, -1: None}  # trailing stop prices per side

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # ── Lorentzian KNN score ─────────────────────────────────────────────
        df['lcm_score'] = calc_lorentzian_classification(
            df,
            k_neighbors=self.k_neighbors,
            history_window=self.history_window,
            rsi_period=self.rsi_period,
            cci_period=self.cci_period,
            adx_period=self.adx_period,
        )

        # ── Supporting indicators ─────────────────────────────────────────────
        df['atr'] = calc_atr(df, self.atr_period)
        adx_vals, _, _ = calc_adx_dmi(df, period=self.adx_period)
        df['adx'] = adx_vals
        df['ema'] = calc_ema(df, period=self.ema_period)

        # ── Entry filter conditions ───────────────────────────────────────────
        if self.entry_filter == 'ADX_ABOVE_20':
            long_filter  = df['adx'] > self.adx_threshold
            short_filter = df['adx'] > self.adx_threshold
        elif self.entry_filter == 'EMA_TREND_FILTER':
            long_filter  = df['Close'] > df['ema']
            short_filter = df['Close'] < df['ema']
        else:
            long_filter  = pd.Series(True, index=df.index)
            short_filter = pd.Series(True, index=df.index)

        # ── Raw signal from KNN vote ──────────────────────────────────────────
        score = df['lcm_score']
        long_raw  = score >= self.signal_threshold
        short_raw = score <= -self.signal_threshold

        df['signal'] = 0
        df.loc[long_raw  & long_filter,  'signal'] = 1
        df.loc[short_raw & short_filter, 'signal'] = -1

        if getattr(self, 'invert_signals', False):
            df['signal'] = -df['signal']

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
        atr  = float(row['atr']) if pd.notna(row['atr']) and row['atr'] > 0 else entry_price * 0.01

        if self.exit_mode == 'CLASSIFICATION_FLIP':
            score = float(row['lcm_score']) if 'lcm_score' in row.index else 0.0
            if side == 1 and score <= -self.signal_threshold:
                return 'EXIT', None
            if side == -1 and score >= self.signal_threshold:
                return 'EXIT', None
            return 'HOLD', None

        # ATR_TRAILING_STOP (default)
        if self._trail[side] is None or self._trail.get('_entry') != entry_price:
            self._trail['_entry'] = entry_price
            self._trail[side] = entry_price - side * self.sl_atr_mult * atr

        if side == 1:
            new_sl = float(row['High']) - self.sl_atr_mult * atr
            if new_sl > self._trail[side]:
                self._trail[side] = new_sl
            if float(row['Low']) <= self._trail[side]:
                return 'SL', self._trail[side]
        else:
            new_sl = float(row['Low']) + self.sl_atr_mult * atr
            if new_sl < self._trail[side]:
                self._trail[side] = new_sl
            if float(row['High']) >= self._trail[side]:
                return 'SL', self._trail[side]

        return 'HOLD', None
