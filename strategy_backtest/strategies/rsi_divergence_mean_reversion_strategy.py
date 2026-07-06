import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_atr, calc_rsi, calc_bollinger_bands, detect_divergence


class RsiDivergenceMeanReversionStrategy(BaseStrategy):
    """
    RSI Divergence Mean Reversion — RSI divergence signals filtered by
    ADX < threshold (ranging market gate). TP at BB midline, SL at ATR multiple.

    Factor Card: factor_library/Mean_Reversion/20260526_rsi_divergence_mean_reversion.md
    Registered IDs: 185 (BTC/4h)

    Logic:
      - Bullish div:  price lower low + RSI higher low → Long if ADX < adx_threshold
      - Bearish div:  price higher high + RSI lower high → Short if ADX < adx_threshold
      - TP:  price crosses BB midline (mean reversion complete)
      - SL:  1.5× ATR from entry
    """

    SIGNAL_PARAMS = frozenset(['rsi_period', 'div_lookback', 'adx_period', 'adx_threshold'])

    OPTIMIZATION_RANGES = {
        'rsi_period':    (7, 21),
        'div_lookback':  (20, 80),
        'adx_period':    (7, 21),
        'adx_threshold': (15, 35),
        'bb_period':     (10, 30),
        'bb_std':        (1.5, 3.0),
        'atr_period':    (7, 21),
        'sl_atr_mult':   (1.0, 3.0),
    }

    def __init__(
        self,
        df: pd.DataFrame,
        rsi_period: int = 13,
        div_lookback: int = 47,
        adx_period: int = 9,
        adx_threshold: float = 32.0026,
        bb_period: int = 11,
        bb_std: float = 1.6958,
        atr_period: int = 10,
        sl_atr_mult: float = 2.6718,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.rsi_period    = int(rsi_period)
        self.div_lookback  = int(div_lookback)
        self.adx_period    = int(adx_period)
        self.adx_threshold = float(adx_threshold)
        self.bb_period     = int(bb_period)
        self.bb_std        = float(bb_std)
        self.atr_period    = int(atr_period)
        self.sl_atr_mult   = float(sl_atr_mult)

        self._s = {
            1:  dict(entry_price=None, sl_price=None),
            -1: dict(entry_price=None, sl_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df    = self.df.copy()
        close = df['Close']

        df['rsi'] = calc_rsi(close, self.rsi_period)
        df['atr'] = calc_atr(df, self.atr_period)

        upper, mid, lower = calc_bollinger_bands(df, self.bb_period, self.bb_std)
        df['bb_mid'] = mid

        adx    = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=self.adx_period)
        adx_ok = adx < self.adx_threshold

        # Divergence signals from library (causal, no look-ahead)
        div_sig = detect_divergence(close, df['rsi'], lookback=self.div_lookback)

        df['signal'] = 0
        df.loc[(div_sig == 1)  & adx_ok, 'signal'] = 1
        df.loc[(div_sig == -1) & adx_ok, 'signal'] = -1

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

        sl = s['sl_price']
        bullish_bar = float(row['Close']) >= float(row['Open'])

        if side == 1:
            sl_hit = float(row['Low'])  <= sl
            if sl_hit: return 'SL', sl
            # TP: price reaches BB midline (mean reversion complete)
            if float(row['High']) >= float(row['bb_mid']):
                return 'TP', float(row['bb_mid'])
        else:
            sl_hit = float(row['High']) >= sl
            if sl_hit: return 'SL', sl
            # TP: price falls to BB midline
            if float(row['Low']) <= float(row['bb_mid']):
                return 'TP', float(row['bb_mid'])

        return 'HOLD', None
