"""
Elite SOL Supertrend + Zero-Lag MACD + FVMA Strategy (long-only)
==============================================================================
Ported from the original OKX-era Elite Combined Portfolio
(paper_trade/combined_portfolio_paper.py, process_sol / SolState). Entry: a
zero-lag-EMA MACD bullish cross, confirmed by price above a volume-weighted
moving average (FVMA) and a bullish custom Supertrend regime. Long-only.
Exit: Supertrend flips bearish (immediate), or price hits an ATR-based stop
derived from the Supertrend's own ATR.

This is the SOL leg of the original ETH+DOT+SOL Elite portfolio that earned
Signal Strive Run B Grade C (score 67.2/100, Sharpe 1.68, +11.9% return, 25.7%
MDD) -- run_id sr_cc302e2431.

Note: the original computed the SL once at entry and held it fixed; here it is
recomputed each bar from the (slow-moving) Supertrend ATR, consistent with how
other ATR-based exits in this codebase work (e.g. exit_signals.exit_atr_tp_sl).
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy


class EliteSolSupertrendZlmacdStrategy(BaseStrategy):
    OPTIMIZATION_RANGES = {}

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.st_period      = kwargs.get('st_period', 10)
        self.st_multiplier  = kwargs.get('st_multiplier', 3.5)
        self.fvma_period    = kwargs.get('fvma_period', 20)
        self.macd_fast      = kwargs.get('macd_fast', 12)
        self.macd_slow      = kwargs.get('macd_slow', 26)
        self.sl_atr_mult    = kwargs.get('sl_atr_mult', 1.0)

    def _compute_state(self, df: pd.DataFrame):
        """Bar-for-bar replica of the original SolState.update() loop."""
        n = len(df)
        C = df['Close'].values
        H = df['High'].values
        L = df['Low'].values
        V = df['Volume'].values if 'Volume' in df.columns else np.zeros(n)

        fast_lag = (self.macd_fast - 1) // 2
        slow_lag = (self.macd_slow - 1) // 2
        alpha_f = 2.0 / (self.macd_fast + 1.0)
        alpha_s = 2.0 / (self.macd_slow + 1.0)

        fvma_arr = np.full(n, np.nan)
        zl_macd_arr = np.full(n, np.nan)
        st_dir_arr = np.full(n, np.nan)
        st_atr_arr = np.full(n, np.nan)

        cv_buf, v_buf = [], []
        fast_closes, slow_closes = [], []
        zlema_fast = zlema_slow = None
        st_atr = None
        prev_close = None
        tr_sum = 0.0
        final_ub = final_lb = None
        cur_st_dir = None

        for i in range(n):
            close, high, low, vol = C[i], H[i], L[i], V[i]

            cv_buf.append(close * vol); v_buf.append(vol)
            if len(cv_buf) > self.fvma_period:
                cv_buf.pop(0); v_buf.pop(0)
            sv = sum(v_buf)
            if sv > 0:
                fvma_arr[i] = sum(cv_buf) / sv

            fast_closes.append(close)
            if len(fast_closes) > fast_lag + 1:
                fast_closes.pop(0)
            slow_closes.append(close)
            if len(slow_closes) > slow_lag + 1:
                slow_closes.pop(0)
            fast_in = close + (close - fast_closes[0]) if len(fast_closes) == fast_lag + 1 else close
            slow_in = close + (close - slow_closes[0]) if len(slow_closes) == slow_lag + 1 else close
            zlema_fast = alpha_f * fast_in + (1 - alpha_f) * zlema_fast if zlema_fast is not None else fast_in
            zlema_slow = alpha_s * slow_in + (1 - alpha_s) * zlema_slow if zlema_slow is not None else slow_in
            zl_macd_arr[i] = zlema_fast - zlema_slow

            if prev_close is not None:
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                if i + 1 <= self.st_period:
                    tr_sum += tr
                    if i + 1 == self.st_period:
                        st_atr = tr_sum / self.st_period
                elif st_atr is not None:
                    st_atr = (st_atr * (self.st_period - 1) + tr) / self.st_period
            st_atr_arr[i] = st_atr if st_atr is not None else np.nan

            hl2 = (high + low) / 2.0
            if st_atr is not None:
                basic_ub = hl2 + self.st_multiplier * st_atr
                basic_lb = hl2 - self.st_multiplier * st_atr
                prev_final_ub, prev_final_lb = final_ub, final_lb
                if prev_final_ub is None:
                    final_ub = basic_ub
                else:
                    final_ub = basic_ub if (basic_ub < prev_final_ub or (prev_close is not None and prev_close > prev_final_ub)) else prev_final_ub
                if prev_final_lb is None:
                    final_lb = basic_lb
                else:
                    final_lb = basic_lb if (basic_lb > prev_final_lb or (prev_close is not None and prev_close < prev_final_lb)) else prev_final_lb
                prev_st_dir = cur_st_dir
                if prev_st_dir is None:
                    cur_st_dir = 1 if close > hl2 else -1
                else:
                    if prev_st_dir == 1 and close < final_lb:
                        cur_st_dir = -1
                    elif prev_st_dir == -1 and close > final_ub:
                        cur_st_dir = 1
                    else:
                        cur_st_dir = prev_st_dir
                st_dir_arr[i] = cur_st_dir

            prev_close = close

        idx = df.index
        return (pd.Series(fvma_arr, index=idx), pd.Series(zl_macd_arr, index=idx),
                pd.Series(st_dir_arr, index=idx), pd.Series(st_atr_arr, index=idx))

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        fvma, zl_macd, st_dir, st_atr = self._compute_state(df)
        df['fvma'] = fvma
        df['zl_macd'] = zl_macd
        df['st_dir'] = st_dir
        df['st_atr'] = st_atr

        prev_macd = zl_macd.shift(1)
        cond_macd = (prev_macd <= 0) & (zl_macd > 0)
        cond_fvma = df['Close'] > fvma
        cond_st = st_dir == 1

        df['signal'] = 0
        df.loc[(cond_macd & cond_fvma & cond_st).fillna(False), 'signal'] = 1  # long-only, matches original

        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float,
                     wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position <= 0:
            return 'HOLD', None
        st_dir = row.get('st_dir', np.nan)
        if not pd.isna(st_dir) and st_dir == -1:
            return 'EXIT', None
        atr = row.get('st_atr', np.nan)
        if not pd.isna(atr) and atr > 0:
            sl_px = entry_price - self.sl_atr_mult * atr
            if float(row['Low']) <= sl_px:
                return 'SL', sl_px
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        return True
