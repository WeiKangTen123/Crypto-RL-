"""
Bollinger Band Breakout + Squeeze Momentum Strategy
==============================================================================
Designed to hit 3% monthly by capturing high-volatility breakouts.

Logic:
1. Squeeze: Bollinger Bands (20, 2) are inside Keltner Channels (20, 1.5).
2. Entry: 
   - LONG: Price breaks ABOVE upper Bollinger Band AND Squeeze is firing (Momentum histogram turns green).
   - SHORT: Price breaks BELOW lower Bollinger Band AND Squeeze is firing (Momentum histogram turns red).
3. Exit:
   - Trailing Stop: Middle Bollinger Band (MA 20).
   - ATR-based dynamic Take Profit.
"""

import numpy as np
import pandas as pd
import ta
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy

class BB_Squeeze_Breakout_Strategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset({'bb_period', 'bb_std', 'kc_multiplier'})

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 29,
        bb_std: float = 3.4961,
        kc_multiplier: float = 1.718,
        atr_multiplier_tp: float = 4.3568,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.kc_multiplier = kc_multiplier
        self.atr_multiplier_tp = atr_multiplier_tp
        
        self._s = {
            1:  dict(entry_price=None, tp_price=None),
            -1: dict(entry_price=None, tp_price=None),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. Bollinger Bands
        bb = ta.volatility.BollingerBands(df['Close'], window=self.bb_period, window_dev=self.bb_std)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_mid'] = bb.bollinger_mavg()
        
        # 2. Keltner Channels (for Squeeze)
        atr = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], window=self.bb_period).average_true_range()
        df['kc_upper'] = df['bb_mid'] + (atr * self.kc_multiplier)
        df['kc_lower'] = df['bb_mid'] - (atr * self.kc_multiplier)
        
        # 3. Squeeze Detection
        df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
        
        # 4. Momentum (Simple MA of high/low midpoint)
        highest_high = df['High'].rolling(window=self.bb_period).max()
        lowest_low = df['Low'].rolling(window=self.bb_period).min()
        midpoint = (highest_high + lowest_low) / 2
        df['momentum'] = ta.trend.ema_indicator(df['Close'] - midpoint, window=self.bb_period)
        
        # 5. Signals
        # Entry when squeeze ends (bands expand) AND momentum is strong
        long_ok = (~df['squeeze_on']) & (df['Close'] > df['bb_upper']) & (df['momentum'] > 0)
        short_ok = (~df['squeeze_on']) & (df['Close'] < df['bb_lower']) & (df['momentum'] < 0)

        signals = np.zeros(len(df), dtype=int)
        long_edge = long_ok & ~long_ok.shift(1, fill_value=False)
        short_edge = short_ok & ~short_ok.shift(1, fill_value=False)
        signals[long_edge.values] = 1
        signals[short_edge.values] = -1
        
        df['signal'] = signals
        self._atr_arr = atr.values
        self._bb_mid_arr = df['bb_mid'].values
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0: return 'HOLD', None
        side = int(np.sign(position))
        s = self._s[side]
        bar_idx = self._bar_index_map.get(row.name, -1)
        
        if entry_price != s['entry_price']:
            atr = self._atr_arr[bar_idx] if bar_idx >= 0 else 0
            s.update(entry_price=entry_price, tp_price=entry_price + side * (self.atr_multiplier_tp * atr))
        
        # 1. Trailing Stop (Middle Band) — use close as fill (bb_mid > close on trigger)
        bb_mid = self._bb_mid_arr[bar_idx]
        curr_price = float(row['Close'])
        if side == 1 and curr_price < bb_mid:
            return 'EXIT', None
        if side == -1 and curr_price > bb_mid:
            return 'EXIT', None
            
        # 2. Dynamic TP
        price_tp = float(row['High']) if side == 1 else float(row['Low'])
        if (side == 1 and price_tp >= s['tp_price']) or (side == -1 and price_tp <= s['tp_price']):
            return 'TP', s['tp_price']

        return 'HOLD', None
