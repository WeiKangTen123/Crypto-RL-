"""
dna.py — StrategyDNA: a composed strategy defined by entry + filters + exit.

StrategyDNA is a thin adapter that plugs into BacktestEngine by implementing
generate_signals() and manage_trade() from BaseStrategy's contract.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy
from strategy_forge.signals.entry_signals import compute_entry_signal, ENTRY_SIGNAL_REGISTRY
from strategy_forge.signals.filter_signals import compute_filter, FILTER_REGISTRY
from strategy_forge.signals.exit_signals import compute_exit, EXIT_REGISTRY
from strategy_forge.indicators.volatility import atr as calc_atr_ind
from strategy_forge.indicators.trend import supertrend as calc_supertrend_ind, parabolic_sar_raw as calc_psar_ind
from strategy_forge.indicators.momentum import rsi as calc_rsi_ind


class StrategyDNA(BaseStrategy):
    """
    A strategy assembled at runtime from modular building blocks.

    Parameters
    ----------
    entry    : name of entry signal (key in ENTRY_SIGNAL_REGISTRY)
    filters  : list of filter names (keys in FILTER_REGISTRY), ANDed together
    exit_method : name of exit method (key in EXIT_REGISTRY)
    params   : dict of numeric parameters passed to all modules
    """

    def __init__(self, df: pd.DataFrame, entry: str, filters: List[str],
                 exit_method: str, params: dict, **kwargs):
        super().__init__(df, **kwargs)
        self.entry       = entry
        self.filters     = filters
        self.exit_method = exit_method
        self.params      = params
        self._bars_held_long  = 0
        self._bars_held_short = 0
        self._exit_state = {}  # persists trailing/chandelier state across bars

    # ── BaseStrategy interface ────────────────────────────────────────────────

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. Entry signal
        raw_signal = compute_entry_signal(self.entry, df, self.params)

        # 2. Apply filters (AND logic: all filters must agree)
        if self.filters:
            allow = pd.Series(True, index=df.index)
            for fname in self.filters:
                allow &= compute_filter(fname, df, self.params)
            raw_signal = raw_signal.where(allow, 0)

        df['signal'] = raw_signal.fillna(0).astype(int)

        # 3. Pre-compute ATR for exit methods that need it (stored in _atr column)
        try:
            df['_atr'] = calc_atr_ind(df, self.params.get('atr_period', 14))
        except Exception:
            df['_atr'] = df['Close'] * 0.02

        # Pre-compute supertrend direction for supertrend_trail exit
        if self.exit_method == 'supertrend_trail':
            try:
                _, st_dir = calc_supertrend_ind(
                    df, self.params.get('st_period', 10), self.params.get('st_multiplier', 3.0)
                )
                df['_st_direction'] = st_dir
            except Exception:
                df['_st_direction'] = 1

        # Pre-compute RSI for rsi_exit
        if self.exit_method == 'rsi_exit':
            try:
                df['_rsi'] = calc_rsi_ind(df, self.params.get('rsi_period', 14))
            except Exception:
                df['_rsi'] = 50.0

        # Pre-compute PSAR for psar_trail exit
        if self.exit_method == 'psar_trail':
            try:
                raw_psar = calc_psar_ind(
                    df,
                    self.params.get('psar_acceleration', 0.02),
                    self.params.get('psar_maximum', 0.2),
                )
                df['_psar'] = raw_psar
                # Previous bar's SAR is the actual trailing stop level
                df['_psar_prev'] = raw_psar.shift(1).bfill()
            except Exception:
                df['_psar']      = df['Close']
                df['_psar_prev'] = df['Close']

        # Pre-compute rolling ATR average for vol_adaptive_sl exit
        if self.exit_method == 'vol_adaptive_sl':
            try:
                vol_ma = self.params.get('vol_ma_period', 50)
                df['_atr_avg'] = df['_atr'].rolling(vol_ma).mean().bfill()
            except Exception:
                df['_atr_avg'] = df['_atr']

        df['_bars_held'] = 0
        self.df = df
        return self.df

    def manage_trade(self, row, position: float, entry_price: float,
                     wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position > 0:
            self._bars_held_long += 1
            bars_held = self._bars_held_long
        elif position < 0:
            self._bars_held_short += 1
            bars_held = self._bars_held_short
        else:
            self._bars_held_long  = 0
            self._bars_held_short = 0
            self._exit_state = {}  # clear when no position open
            bars_held = 0

        # Merge static params with persistent exit state (trailing/chandelier need this)
        self._exit_state['_bars_held'] = bars_held
        p = {**self.params, **self._exit_state}
        action, price = compute_exit(self.exit_method, row, position, entry_price, p)

        # Capture any state keys written by exit function back into persistent state
        for k, v in p.items():
            if k not in self.params:
                self._exit_state[k] = v

        if action in ('TP', 'SL', 'EXIT'):
            self._bars_held_long  = 0
            self._bars_held_short = 0
            self._exit_state = {}   # clear trailing/chandelier state between trades

        return action, price

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            'entry':       self.entry,
            'filters':     self.filters,
            'exit_method': self.exit_method,
            'params':      self.params,
        }

    @classmethod
    def from_dict(cls, df: pd.DataFrame, d: dict) -> 'StrategyDNA':
        return cls(df, d['entry'], d['filters'], d['exit_method'], d['params'])

    def __repr__(self):
        return (f"StrategyDNA(entry={self.entry!r}, filters={self.filters}, "
                f"exit={self.exit_method!r}, params={self.params})")
