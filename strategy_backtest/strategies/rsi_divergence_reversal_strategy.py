import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class RSIDivergenceReversalStrategy(BaseStrategy):
    """
    RSI Divergence Reversal Strategy.
    Identifies bullish/bearish divergences between Price and RSI.
    mode='both'       — trade bullish and bearish divergences
    mode='long_only'  — only bullish divergences (long trades)
    mode='short_only' — only bearish divergences (short trades)
    """

    OPTIMIZATION_RANGES = {
        'rsi_period':        (7,  21),
        'lookback':          (10, 60),
        'pivot_window':      (2,  8),
        'rsi_threshold_low': (20, 50),   # wider — allow divergences even at mid-RSI
        'rsi_threshold_high':(50, 80),
        'taker_threshold':   (0.45, 0.65),
        'sl_atr_mult':       (1.0, 4.0),
        'tp_rsi':            (50, 80),
        'mode':              ['both', 'long_only', 'short_only'],
        'use_taker_filter':  [True, False],  # Optuna can turn off the taker gate
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.rsi_period        = kwargs.get('rsi_period', 14)
        self.lookback          = kwargs.get('lookback', 30)
        self.pivot_window      = kwargs.get('pivot_window', 5)
        self.rsi_threshold_low = kwargs.get('rsi_threshold_low', 30)
        self.rsi_threshold_high= kwargs.get('rsi_threshold_high', 70)
        self.taker_threshold   = kwargs.get('taker_threshold', 0.5)
        self.tp_rsi            = kwargs.get('tp_rsi', 70)
        self.sl_atr_mult       = kwargs.get('sl_atr_mult', 2.0)
        self.mode              = kwargs.get('mode', 'both')
        self.use_taker_filter  = kwargs.get('use_taker_filter', True)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        w  = self.pivot_window

        df['rsi'] = talib.RSI(df['Close'], timeperiod=self.rsi_period)
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)

        if 'taker_buy_base_vol' in df.columns and 'Volume' in df.columns:
            taker_vol = pd.to_numeric(df['taker_buy_base_vol'], errors='coerce')
            total_vol = pd.to_numeric(df['Volume'], errors='coerce')
            df['taker_ratio'] = taker_vol / total_vol.replace(0, np.nan)
        else:
            df['taker_ratio'] = 0.5

        df['signal'] = 0

        # --- Bullish divergence tracking ---
        last_bull_low_price = np.nan
        last_bull_low_rsi   = np.nan

        # --- Bearish divergence tracking ---
        last_bear_high_price = np.nan
        last_bear_high_rsi   = np.nan

        for i in range(self.lookback, len(df)):
            check = i - w
            if check < w:
                continue

            # ── BULLISH DIVERGENCE ────────────────────────────────────────────
            if self.mode in ('both', 'long_only'):
                is_pivot_low = (
                    df['Low'].iloc[check] ==
                    df['Low'].iloc[check - w : check + w + 1].min()
                )
                if is_pivot_low:
                    curr_price = df['Low'].iloc[check]
                    curr_rsi   = df['rsi'].iloc[check]
                    if not np.isnan(last_bull_low_price) and not np.isnan(curr_rsi):
                        if (curr_price < last_bull_low_price
                                and curr_rsi > last_bull_low_rsi
                                and last_bull_low_rsi < self.rsi_threshold_low):
                            taker_ok = (not self.use_taker_filter or
                                        df['taker_ratio'].iloc[i] > self.taker_threshold)
                            if taker_ok:
                                df.loc[df.index[i], 'signal'] = 1
                    last_bull_low_price = curr_price
                    last_bull_low_rsi   = curr_rsi

            # ── BEARISH DIVERGENCE ────────────────────────────────────────────
            if self.mode in ('both', 'short_only'):
                is_pivot_high = (
                    df['High'].iloc[check] ==
                    df['High'].iloc[check - w : check + w + 1].max()
                )
                if is_pivot_high:
                    curr_price = df['High'].iloc[check]
                    curr_rsi   = df['rsi'].iloc[check]
                    if not np.isnan(last_bear_high_price) and not np.isnan(curr_rsi):
                        if (curr_price > last_bear_high_price
                                and curr_rsi < last_bear_high_rsi
                                and last_bear_high_rsi > self.rsi_threshold_high):
                            taker_ok = (not self.use_taker_filter or
                                        df['taker_ratio'].iloc[i] < (1.0 - self.taker_threshold))
                            if taker_ok:
                                df.loc[df.index[i], 'signal'] = -1
                    last_bear_high_price = curr_price
                    last_bear_high_rsi   = curr_rsi

        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        rsi = getattr(row, 'rsi', np.nan)
        atr = getattr(row, 'atr', np.nan)

        if position > 0:
            if not np.isnan(rsi) and rsi > self.tp_rsi:
                return 'EXIT', float(row['Close'])
            if not np.isnan(atr):
                sl = entry_price - self.sl_atr_mult * atr
                if float(row['Low']) < sl:
                    return 'SL', sl
        elif position < 0:
            tp_rsi_short = 100 - self.tp_rsi
            if not np.isnan(rsi) and rsi < tp_rsi_short:
                return 'EXIT', float(row['Close'])
            if not np.isnan(atr):
                sl = entry_price + self.sl_atr_mult * atr
                if float(row['High']) > sl:
                    return 'SL', sl

        return 'HOLD', None
