"""
Fair Value Gap (FVG) Recovery Strategy
==============================================================================
Category: Market Structure
Hypothesis: FVGs are price inefficiencies that the market tends to "fill" or 
           "rebalance" before continuing a trend.

Logic:
1. Identify Bullish/Bearish FVG (3-candle sequence).
2. Wait for price to retrace into the gap.
3. Entry: Price hits the 50% midpoint (Consequent Encroachment - CE).
4. SL: Wick of the first candle (origin of the gap).
5. TP: Swing High/Low created by the impulsive move (3rd candle).
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
import os



from strategy_backtest.base_strategy import BaseStrategy


class FVG_Recovery_Strategy(BaseStrategy):

    SIGNAL_PARAMS = frozenset({
        'min_gap_pct',      # Minimum size of the gap relative to price to filter noise
        'retrace_depth',    # How deep into the gap to entry (0.5 = 50% CE)
        'ema_period',       # EMA for trend filter
        'use_trend_filter', # Whether to use trend filter
        'require_confirmation', # Wait for a candle to close in the right direction
        'tp_multiplier',    # Multiply the standard TP distance
    })

    def __init__(
        self,
        df: pd.DataFrame,
        min_gap_pct: float = 0.0241,
        retrace_depth: float = 0.6789,
        ema_period: int = 171,
        use_trend_filter: bool = True,
        require_confirmation: bool = True,
        tp_multiplier: float = 4.1718,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.min_gap_pct = min_gap_pct
        self.retrace_depth = retrace_depth
        self.ema_period = ema_period
        self.use_trend_filter = use_trend_filter
        self.require_confirmation = require_confirmation
        self.tp_multiplier = tp_multiplier
        
        # State tracking for trades
        self._s = {
            1:  dict(sl_price=None, tp_price=None),
            -1: dict(sl_price=None, tp_price=None),
        }
        self._bar_index_map = {ts: i for i, ts in enumerate(df.index)}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        open_p = df['Open'].values
        
        signals = np.zeros(len(df), dtype=int)
        
        # Trend Filter
        ema_trend = df['Close'].ewm(span=self.ema_period, adjust=False).mean().values
        
        # Active Gaps: {'trigger': price, 'sl': price, 'tp': price, 'touched': bool, 'side': int}
        active_gaps = []
        
        # Add SL/TP columns
        df['fvg_sl'] = np.nan
        df['fvg_tp'] = np.nan
        
        for i in range(2, len(df)):
            # 1. IDENTIFY NEW FVGs
            
            # Bullish FVG
            if high[i-2] < low[i]:
                gap_size = low[i] - high[i-2]
                if gap_size > close[i] * self.min_gap_pct:
                    active_gaps.append({
                        'side': 1, 'trigger': high[i-2] + (gap_size * (1 - self.retrace_depth)),
                        'sl': high[i-2], 'tp_base': low[i], 'target': high[i],
                        'bottom': high[i-2], 'top': low[i], 'touched': False
                    })
            
            # Bearish FVG
            if low[i-2] > high[i]:
                gap_size = low[i-2] - high[i]
                if gap_size > close[i] * self.min_gap_pct:
                    active_gaps.append({
                        'side': -1, 'trigger': low[i-2] - (gap_size * (1 - self.retrace_depth)),
                        'sl': low[i-2], 'tp_base': high[i], 'target': low[i],
                        'bottom': high[i], 'top': low[i-2], 'touched': False
                    })
            
            # 2. PROCESS ACTIVE GAPS
            for gap in list(active_gaps):
                # Check for invalidation (Full candle body closes through the gap origin)
                if gap['side'] == 1 and close[i] < gap['bottom']:
                    active_gaps.remove(gap); continue
                if gap['side'] == -1 and close[i] > gap['top']:
                    active_gaps.remove(gap); continue

                # Stage 1: Check for retrace touch
                if not gap['touched']:
                    if low[i] <= gap['trigger'] <= high[i]:
                        gap['touched'] = True
                
                # Stage 2: Check for confirmation candle
                if gap['touched']:
                    entry_signal = False
                    if self.require_confirmation:
                        # Bullish candle for Long, Bearish for Short
                        if gap['side'] == 1 and close[i] > open_p[i]: entry_signal = True
                        if gap['side'] == -1 and close[i] < open_p[i]: entry_signal = True
                    else:
                        entry_signal = True # Entry on touch bar
                    
                    if entry_signal:
                        # Trend Filter check at entry
                        if self.use_trend_filter:
                            if gap['side'] == 1 and close[i] <= ema_trend[i]: entry_signal = False
                            if gap['side'] == -1 and close[i] >= ema_trend[i]: entry_signal = False
                        
                        if entry_signal:
                            signals[i] = gap['side']
                            # Calculate Final TP with multiplier
                            # Standard TP is the distance to the target (swing high/low)
                            dist = abs(gap['target'] - close[i])
                            df.at[df.index[i], 'fvg_sl'] = gap['sl']
                            df.at[df.index[i], 'fvg_tp'] = close[i] + gap['side'] * (dist * self.tp_multiplier)
                            active_gaps.remove(gap)
                            break # Only one signal per bar
                            
        df['signal'] = signals
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0.0,
    ) -> Tuple[str, Optional[float]]:
        
        if position == 0:
            return 'HOLD', None
            
        side = int(np.sign(position))
        s = self._s[side]
        
        if entry_price != getattr(self, f'_last_entry_price_{side}', None):
            setattr(self, f'_last_entry_price_{side}', entry_price)
            # Lookup SL/TP from the dataframe using the timestamp (row.name)
            # Since signals are generated on the bar we enter, we can find the levels there.
            # But wait, entry happens on the same bar as the signal.
            fvg_sl = self.df.at[row.name, 'fvg_sl']
            fvg_tp = self.df.at[row.name, 'fvg_tp']
            
            s['sl_price'] = fvg_sl if not np.isnan(fvg_sl) else entry_price * (1 - side * 0.02)
            s['tp_price'] = fvg_tp if not np.isnan(fvg_tp) else entry_price * (1 + side * 0.05)

        price_low = float(row['Low'])
        price_high = float(row['High'])

        if side == 1:
            if price_low  <= s['sl_price']: return 'SL', s['sl_price']
            if price_high >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if price_high >= s['sl_price']: return 'SL', s['sl_price']
            if price_low  <= s['tp_price']: return 'TP', s['tp_price']

        return 'HOLD', None
