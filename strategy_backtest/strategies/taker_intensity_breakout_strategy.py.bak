import numpy as np
import pandas as pd
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_taker_intensity, calc_bollinger_bands

class TIPBreakoutStrategy(BaseStrategy):
    """
    Taker-Intensity Participation (TIP) Breakout Strategy
    
    Logic:
      1. Volatility Filter: Price > Upper Bollinger Band.
      2. Aggression Filter: Taker Buy Volume / Total Volume > threshold (e.g., 0.55).
      3. Urgency Filter: num_trades > MA(num_trades, 24) + 2*STD(num_trades, 24).
    """

    SIGNAL_PARAMS = frozenset([
        'bb_period', 'bb_std', 'intensity_period', 'intensity_std', 'taker_threshold', 'sl_atr_mult', 'tp_atr_mult'
    ])

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 46,
        bb_std: float = 1.1743,
        intensity_period: int = 24,
        intensity_std: float = 2.8712,
        taker_threshold: float = 0.5541,
        sl_atr_mult: float = 1.77,
        tp_atr_mult: float = 3.7271,
        max_hold_bars: int = 157,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.intensity_period = intensity_period
        self.intensity_std = intensity_std
        self.taker_threshold = taker_threshold
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.max_hold_bars = max_hold_bars

        # Per-side state for trade management
        self._s = {
            1:  dict(entry_price=0.0, sl_price=0.0, bar_count=0),
            -1: dict(entry_price=0.0, sl_price=0.0, bar_count=0),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # 1. Bollinger Bands
        bb_mid, bb_up, bb_low = calc_bollinger_bands(df, self.bb_period, self.bb_std)
        df['bb_up'] = bb_up
        df['bb_low'] = bb_low
        df['prev_bb_up'] = bb_up.shift(1)
        df['prev_bb_low'] = bb_low.shift(1)

        # 2. Taker Intensity
        intensity_zscore, taker_ratio = calc_taker_intensity(df, self.intensity_period, self.intensity_std)
        df['intensity'] = intensity_zscore
        df['taker_ratio'] = taker_ratio
        
        # 3. ATR for Take Profit calculation
        from strategy_backtest.library import calc_atr
        df['atr'] = calc_atr(df, 14)

        # Signals
        # Long: Close > Upper BB AND Taker Ratio > Threshold AND Intensity Z-Score > Threshold
        long_cond = (
            (df['Close'] > df['bb_up']) &
            (df['taker_ratio'] > self.taker_threshold) &
            (df['intensity'] > self.intensity_std)
        )

        # Short: Close < Lower BB AND Taker Ratio < (1 - Threshold) AND Intensity Z-Score > Threshold
        short_cond = (
            (df['Close'] < df['bb_low']) &
            (df['taker_ratio'] < (1.0 - self.taker_threshold)) &
            (df['intensity'] > self.intensity_std)
        )

        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1
        signals[short_cond] = -1

        df['signal'] = signals
        self.df = df
        return df

    def manage_trade(self, row, position, entry_price, wallet=0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        s = self._s[side]

        # Initialize trade state if new
        if entry_price != s['entry_price']:
            s['entry_price'] = entry_price
            
            # Use dynamic ATR for take profit and stop loss targets
            atr = float(getattr(row, 'atr', entry_price * 0.01))
            s['sl_price'] = entry_price - (side * atr * self.sl_atr_mult)
            s['tp_target'] = entry_price + (side * atr * self.tp_atr_mult)
            s['bar_count'] = 0

        s['bar_count'] += 1
        curr_price = float(row['Close'])
        
        tp_price = s['tp_target']
        if side == 1:
            if float(row['Low'])  <= s['sl_price']: return 'SL', s['sl_price']

            if float(row['High']) >= tp_price: return 'TP', tp_price
        else:
            if float(row['High']) >= s['sl_price']: return 'SL', s['sl_price']

            if float(row['Low'])  <= tp_price: return 'TP', tp_price

        # 3. Exit Logic: Price closes back inside BB (Mean Reversion confirmation)
        if side == 1 and curr_price < float(row['bb_up']):
            return 'EXIT', None
        if side == -1 and curr_price > float(row['bb_low']):
            return 'EXIT', None

        # 4. Time Exit
        if s['bar_count'] >= self.max_hold_bars:
            return 'EXIT', None

        return 'HOLD', None

