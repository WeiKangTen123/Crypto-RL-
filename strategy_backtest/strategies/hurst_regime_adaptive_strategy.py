import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_zscore


class HurstRegimeAdaptiveStrategy(BaseStrategy):
    """
    Hurst Regime Adaptive Strategy — inspired by DFA fractal analysis research.

    Source paper: Fujimoto et al. (2025) "Enhanced scaling crossover detection in
    long-range correlated time series" — Chaos, Solitons & Fractals: X 14 (2025).

    Uses the Variance Ratio (Lo-MacKinlay 1988) as a fast proxy for the Hurst exponent:
        VR = Var(k-bar returns) / (k * Var(1-bar returns))
        VR > 1: persistent process (H > 0.5) → trending market
        VR < 1: anti-persistent process (H < 0.5) → mean-reverting market
        VR ≈ 1: random walk (H ≈ 0.5) → no detectable regime

    Regime-adaptive signal selection:
        TRENDING  (VR > 1 + vr_band): momentum — buy breakouts, follow the trend
        REVERTING (VR < 1 - vr_band): mean-reversion — fade extreme deviations
        NEUTRAL   (|VR - 1| < vr_band): flat — no position

    Momentum entry (trending):  close crosses above/below N-bar rolling high/low
    Reversion entry (reverting): z-score of close exceeds ±threshold (oversold/overbought)
    """

    SIGNAL_PARAMS = frozenset([
        'vr_window', 'vr_k', 'vr_band',
        'mom_period', 'rev_zscore_period', 'rev_threshold',
    ])

    OPTIMIZATION_RANGES = {
        'vr_window':         (50, 200),
        'vr_k':              (4, 20),
        'vr_band':           (0.05, 0.40),
        'mom_period':        (5, 30),
        'rev_zscore_period': (10, 60),
        'rev_threshold':     (1.0, 3.0),
        'atr_period':        (7, 21),
        'sl_atr_mult':       (1.0, 3.0),
        'atr_trail_mult':    (2.0, 5.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        vr_window: int = 167,
        vr_k: int = 11,
        vr_band: float = 0.3781,
        mom_period: int = 26,
        rev_zscore_period: int = 19,
        rev_threshold: float = 2.5796,
        atr_period: int = 7,
        sl_atr_mult: float = 1.3872,
        atr_trail_mult: float = 4.0786,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.vr_window         = int(vr_window)
        self.vr_k              = int(vr_k)
        self.vr_band           = float(vr_band)
        self.mom_period        = int(mom_period)
        self.rev_zscore_period = int(rev_zscore_period)
        self.rev_threshold     = float(rev_threshold)
        self.atr_period        = int(atr_period)
        self.sl_atr_mult       = float(sl_atr_mult)
        self.atr_trail_mult    = float(atr_trail_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def _calc_variance_ratio(self, returns: pd.Series) -> pd.Series:
        """
        Rolling variance ratio proxy for Hurst exponent.
        VR(k) = Var(k-bar returns) / (k * Var(1-bar returns))
        """
        var_1 = returns.rolling(self.vr_window).var()
        ret_k = returns.rolling(self.vr_k).sum()
        var_k = ret_k.rolling(self.vr_window).var()
        vr = var_k / (self.vr_k * var_1.replace(0, np.nan))
        return vr.clip(0.0, 3.0)

    def generate_signals(self) -> pd.DataFrame:
        df    = self.df.copy()
        close = df['Close'].astype(float)
        ret_1 = close.pct_change(1)

        # ── Regime detection ──────────────────────────────────────────────────
        vr = self._calc_variance_ratio(ret_1)

        trending  = vr > (1 + self.vr_band)
        reverting = vr < (1 - self.vr_band)

        # ── Momentum signal (trending regime) ─────────────────────────────────
        roll_high = close.rolling(self.mom_period).max()
        roll_low  = close.rolling(self.mom_period).min()
        # Breakout of N-bar range
        mom_long  = trending & (close >= roll_high.shift(1))
        mom_short = trending & (close <= roll_low.shift(1))

        # ── Mean-reversion signal (reverting regime) ──────────────────────────
        zscore    = calc_zscore(close, self.rev_zscore_period)
        rev_long  = reverting & (zscore < -self.rev_threshold)
        rev_short = reverting & (zscore >  self.rev_threshold)

        # ── Combine signals ───────────────────────────────────────────────────
        df['vr']     = vr
        df['zscore'] = zscore
        df['atr']    = calc_atr(df, self.atr_period)

        df['signal'] = 0
        df.loc[mom_long  | rev_long,  'signal'] = 1
        df.loc[mom_short | rev_short, 'signal'] = -1

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

        if s['entry_price'] != entry_price:
            s['entry_price'] = entry_price
            s['sl_price']    = entry_price - side * (self.sl_atr_mult * atr)

        if side == 1:
            new_sl = float(row['High']) - self.atr_trail_mult * atr
            if new_sl > s['sl_price']:
                s['sl_price'] = new_sl
            if float(row['Low']) <= s['sl_price']:
                return 'SL', s['sl_price']
        else:
            new_sl = float(row['Low']) + self.atr_trail_mult * atr
            if new_sl < s['sl_price']:
                s['sl_price'] = new_sl
            if float(row['High']) >= s['sl_price']:
                return 'SL', s['sl_price']

        return 'HOLD', None
