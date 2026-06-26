import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class WaveTrendMFIDivergenceStrategy(BaseStrategy):
    """
    WaveTrend + MFI Divergence Strategy
    
    Logic:
      - WaveTrend: Identifies exhaustion points.
      - MFI Divergence: Confirms reversals with volume-weighted momentum.
      - Trend Filter: 200 EMA.
    """

    OPTIMIZATION_RANGES = {
        'wt_n1':             (5,   20),
        'wt_n2':             (10,  50),
        'wt_oversold':       (-80, -20),
        'wt_overbought':     (40,  80),
        'mfi_period':        (5,   30),
        'divergence_lookback':(5,  30),
        'tp_rr':             (1.0,  5.0),
        'sl_atr_mult':       (0.5,  3.0),
        'signal_mode':       ['STRICT_DIVERGENCE', 'WT_CROSS_ONLY'],
    }

    SIGNAL_PARAMS = frozenset([
        'wt_n1', 'wt_n2', 'wt_oversold', 'wt_overbought',
        'mfi_period', 'ema_period', 'divergence_lookback', 'signal_mode',
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        wt_n1: int = 8,
        wt_n2: int = 30,
        wt_oversold: int = -40,
        wt_overbought: int = 77,
        mfi_period: int = 10,
        ema_period: int = 148,
        divergence_lookback: int = 12,
        tp_rr: float = 1.6425,
        sl_atr_mult: float = 1.8711,
        signal_mode: str = 'STRICT_DIVERGENCE',
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.wt_n1 = wt_n1
        self.wt_n2 = wt_n2
        self.wt_oversold = wt_oversold
        self.wt_overbought = wt_overbought
        self.mfi_period = mfi_period
        self.ema_period = ema_period
        self.divergence_lookback = divergence_lookback
        self.tp_rr = tp_rr
        self.sl_atr_mult = sl_atr_mult
        self.signal_mode = signal_mode

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. WaveTrend Calculation
        ap = (df['High'] + df['Low'] + df['Close']) / 3
        esa = ta.trend.ema_indicator(ap, window=self.wt_n1)
        d = ta.trend.ema_indicator(abs(ap - esa), window=self.wt_n1)
        ci = (ap - esa) / (0.015 * d)
        df['wt1'] = ta.trend.ema_indicator(ci, window=self.wt_n2)
        df['wt2'] = df['wt1'].rolling(window=4).mean()

        # 2. MFI Calculation
        df['mfi'] = ta.volume.money_flow_index(
            high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=self.mfi_period
        )

        # 3. ATR
        df['ATR'] = ta.volatility.average_true_range(
            high=df['High'], low=df['Low'], close=df['Close'], window=14
        )

        wt1 = df['wt1'].values
        wt2 = df['wt2'].values
        mfi = df['mfi'].values
        low = df['Low'].values
        high = df['High'].values
        
        signals = np.zeros(len(df), dtype=int)
        
        for i in range(len(df)):
            if i < self.divergence_lookback or np.isnan(wt1[i]) or np.isnan(mfi[i]):
                continue

            wt_cross_up   = (wt1[i] > wt2[i]) and (wt1[i-1] <= wt2[i-1]) and (wt1[i] < self.wt_oversold)
            wt_cross_down = (wt1[i] < wt2[i]) and (wt1[i-1] >= wt2[i-1]) and (wt1[i] > self.wt_overbought)

            if self.signal_mode == 'WT_CROSS_ONLY':
                # Relaxed: fire on WT cross at extreme levels without MFI divergence
                if wt_cross_up:
                    signals[i] = 1
                elif wt_cross_down:
                    signals[i] = -1
            else:
                # STRICT_DIVERGENCE: require MFI divergence confirmation
                if wt_cross_up:
                    lookback_slice_price = low[i-self.divergence_lookback : i]
                    lookback_slice_mfi   = mfi[i-self.divergence_lookback : i]
                    min_low_idx = np.argmin(lookback_slice_price)
                    if low[i] < lookback_slice_price[min_low_idx] and \
                       mfi[i] > lookback_slice_mfi[min_low_idx]:
                        signals[i] = 1

                if wt_cross_down:
                    lookback_slice_price = high[i-self.divergence_lookback : i]
                    lookback_slice_mfi   = mfi[i-self.divergence_lookback : i]
                    max_high_idx = np.argmax(lookback_slice_price)
                    if high[i] > lookback_slice_price[max_high_idx] and \
                       mfi[i] < lookback_slice_mfi[max_high_idx]:
                        signals[i] = -1

        df['signal'] = signals
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        atr = getattr(row, 'ATR', 0)
        
        if side == 1:
            sl_price = entry_price - self.sl_atr_mult * atr if atr > 0 else entry_price * 0.98
            tp_price = entry_price + (entry_price - sl_price) * self.tp_rr
            if float(row.Low)  <= sl_price: return 'SL', sl_price
            if float(row.High) >= tp_price: return 'TP', tp_price

        elif side == -1:
            sl_price = entry_price + self.sl_atr_mult * atr if atr > 0 else entry_price * 1.02
            tp_price = entry_price - (sl_price - entry_price) * self.tp_rr
            if float(row.High) >= sl_price: return 'SL', sl_price
            if float(row.Low)  <= tp_price: return 'TP', tp_price

        return 'HOLD', None
