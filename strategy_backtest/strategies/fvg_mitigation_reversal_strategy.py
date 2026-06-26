import pandas as pd
import numpy as np
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class FVGMitigationReversalStrategy(BaseStrategy):
    """
    Fair Value Gap (FVG) Mitigation Reversal Strategy.
    Identifies FVGs and enters when price mitigates (returns to) the gap.
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.min_gap_pct = kwargs.get('min_gap_pct', 0.005)
        self.tp_multiplier = kwargs.get('tp_multiplier', 2.0)
        self.atr_period = kwargs.get('atr_period', 14)
        self._active_fvgs = [] # List of dicts: {'type': 'bullish'/'bearish', 'top': float, 'bottom': float, 'origin_idx': int}

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        signals = np.zeros(len(df), dtype=int)
        
        # 1. Identify FVGs
        # Bullish FVG: Low[i] > High[i-2]
        # Bearish FVG: High[i] < Low[i-2]
        
        for i in range(2, len(df)):
            # Check for new Bullish FVG
            if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                gap_size = (df['Low'].iloc[i] - df['High'].iloc[i-2]) / df['High'].iloc[i-2]
                if gap_size >= self.min_gap_pct:
                    self._active_fvgs.append({
                        'type': 'bullish',
                        'top': df['Low'].iloc[i],
                        'bottom': df['High'].iloc[i-2],
                        'origin_idx': i
                    })
            
            # Check for new Bearish FVG
            if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                gap_size = (df['Low'].iloc[i-2] - df['High'].iloc[i]) / df['Low'].iloc[i-2]
                if gap_size >= self.min_gap_pct:
                    self._active_fvgs.append({
                        'type': 'bearish',
                        'top': df['Low'].iloc[i-2],
                        'bottom': df['High'].iloc[i],
                        'origin_idx': i
                    })
            
            # 2. Check for Mitigation (Entry)
            # We look for price entering the gap from the previous active FVGs
            # To keep it simple for this vectorized-ish approach, we'll only check the most recent FVG of each type
            
            # This is hard to do purely vectorized if we want to track multiple FVGs.
            # Let's just use the single most recent FVG of each type for simplicity in signals.
            
        # Re-implementing more vectorized for speed
        df['bullish_fvg_top'] = np.nan
        df['bullish_fvg_bottom'] = np.nan
        df['bearish_fvg_top'] = np.nan
        df['bearish_fvg_bottom'] = np.nan
        
        # Bullish FVG detection
        bull_fvg_mask = (df['Low'] > df['High'].shift(2)) & ((df['Low'] - df['High'].shift(2)) / df['High'].shift(2) >= self.min_gap_pct)
        df.loc[bull_fvg_mask, 'bullish_fvg_top'] = df['Low']
        df.loc[bull_fvg_mask, 'bullish_fvg_bottom'] = df['High'].shift(2)
        
        # Bearish FVG detection
        bear_fvg_mask = (df['High'] < df['Low'].shift(2)) & ((df['Low'].shift(2) - df['High']) / df['Low'].shift(2) >= self.min_gap_pct)
        df.loc[bear_fvg_mask, 'bearish_fvg_top'] = df['Low'].shift(2)
        df.loc[bear_fvg_mask, 'bearish_fvg_bottom'] = df['High']
        
        # Forward fill the gaps to "remember" them
        df['last_bull_top'] = df['bullish_fvg_top'].ffill()
        df['last_bull_bottom'] = df['bullish_fvg_bottom'].ffill()
        df['last_bear_top'] = df['bearish_fvg_top'].ffill()
        df['last_bear_bottom'] = df['bearish_fvg_bottom'].ffill()
        
        df['signal'] = 0

        # Entry logic: Price pulls back into the most recent FVG
        long_mitigation = (
            df['last_bull_top'].notna() & df['last_bull_bottom'].notna() &
            (df['Low'] <= df['last_bull_top']) & (df['Low'] >= df['last_bull_bottom']) &
            (~bull_fvg_mask)
        )
        short_mitigation = (
            df['last_bear_top'].notna() & df['last_bear_bottom'].notna() &
            (df['High'] >= df['last_bear_bottom']) & (df['High'] <= df['last_bear_top']) &
            (~bear_fvg_mask)
        )

        df.loc[long_mitigation, 'signal'] = 1
        df.loc[short_mitigation, 'signal'] = -1
        
        self.df = df
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
            
        side = np.sign(position)
        
        # Use a fixed SL and TP based on gap width
        if side == 1:
            gap_width = row['last_bull_top'] - row['last_bull_bottom']
            tp_price = entry_price + (self.tp_multiplier * gap_width)
            sl_price = row['last_bull_bottom']
            if row['Low']  <= sl_price: return 'SL', sl_price

            if row['High'] >= tp_price: return 'TP', tp_price
        else:
            gap_width = row['last_bear_top'] - row['last_bear_bottom']
            tp_price = entry_price - (self.tp_multiplier * gap_width)
            sl_price = row['last_bear_top']
            if row['High'] >= sl_price: return 'SL', sl_price

            if row['Low']  <= tp_price: return 'TP', tp_price

        return 'HOLD', None
