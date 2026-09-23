"""
Order Block (SMC) Reversal Strategy - Refined
==============================================================================
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class OrderBlockSMCStrategy(BaseStrategy):
    SIGNAL_PARAMS = frozenset({
        'lookback',         # Lookback for BOS detection
        'ob_volume_mult',   # OB candle volume must be > SMA(Volume) * mult
        'tp_rr',            # Take profit Reward-to-Risk ratio
    })

    def __init__(
        self,
        df: pd.DataFrame,
        lookback: int = 7,
        ob_volume_mult: float = 2.8206,
        tp_rr: float = 3.821,
        **kwargs,
    ):
        super().__init__(df, **kwargs)
        self.lookback = lookback
        self.ob_volume_mult = ob_volume_mult
        self.tp_rr = tp_rr
        
        self._s = {
            1:  dict(sl_price=None, tp_price=None),
            -1: dict(sl_price=None, tp_price=None),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        open_p = df['Open'].values
        volume = df['Volume'].values
        
        signals = np.zeros(len(df), dtype=int)
        df['ob_sl'] = np.nan
        df['ob_tp'] = np.nan
        
        # Donchian Channels for BOS
        df['hh'] = df['High'].shift(1).rolling(window=self.lookback).max()
        df['ll'] = df['Low'].shift(1).rolling(window=self.lookback).min()
        hh = df['hh'].values
        ll = df['ll'].values
        
        vol_sma = df['Volume'].rolling(window=50).mean().values
        
        # Active Order Blocks
        obs = []
        
        for i in range(self.lookback + 1, len(df)):
            # 1. Detect BOS and Create OB
            
            # Bullish BOS: Close breaks last HH
            if close[i] > hh[i]:
                # Find the last bearish candle before this breakout move
                for j in range(i - 1, i - self.lookback, -1):
                    if close[j] < open_p[j]:
                        if np.isnan(vol_sma[j]) or volume[j] >= vol_sma[j] * self.ob_volume_mult:
                            obs.append({
                                'side': 1, 'top': high[j], 'bottom': low[j], 'mitigated': False
                            })
                            break
            
            # Bearish BOS: Close breaks last LL
            if close[i] < ll[i]:
                # Find the last bullish candle before this breakout move
                for j in range(i - 1, i - self.lookback, -1):
                    if close[j] > open_p[j]:
                        if np.isnan(vol_sma[j]) or volume[j] >= vol_sma[j] * self.ob_volume_mult:
                            obs.append({
                                'side': -1, 'top': high[j], 'bottom': low[j], 'mitigated': False
                            })
                            break

            # 2. Check for mitigation and signals
            for ob in obs:
                if ob['mitigated']: continue
                
                # Invalidation: Price closes beyond the OB
                if ob['side'] == 1 and close[i] < ob['bottom']:
                    ob['mitigated'] = True; continue
                if ob['side'] == -1 and close[i] > ob['top']:
                    ob['mitigated'] = True; continue
                
                # Entry Signal: Price enters the OB (retrace)
                if ob['side'] == 1:
                    if low[i] <= ob['top'] and close[i] > ob['bottom']:
                        signals[i] = 1
                        risk = max(ob['top'] - ob['bottom'], close[i] * 0.001) # Min risk floor
                        df.at[df.index[i], 'ob_sl'] = ob['bottom']
                        df.at[df.index[i], 'ob_tp'] = close[i] + (risk * self.tp_rr)
                        ob['mitigated'] = True
                        break
                else:
                    if high[i] >= ob['bottom'] and close[i] < ob['top']:
                        signals[i] = -1
                        risk = max(ob['top'] - ob['bottom'], close[i] * 0.001)
                        df.at[df.index[i], 'ob_sl'] = ob['top']
                        df.at[df.index[i], 'ob_tp'] = close[i] - (risk * self.tp_rr)
                        ob['mitigated'] = True
                        break
                    
        df['signal'] = signals
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
            
        side = int(np.sign(position))
        s = self._s[side]
        
        if entry_price != getattr(self, f'_last_entry_price_{side}', None):
            setattr(self, f'_last_entry_price_{side}', entry_price)
            # Use self.df directly to ensure we get the columns
            sl = self.df.at[row.name, 'ob_sl']
            tp = self.df.at[row.name, 'ob_tp']
            
            s['sl_price'] = sl if not np.isnan(sl) else entry_price * (1 - side * 0.02)
            s['tp_price'] = tp if not np.isnan(tp) else entry_price * (1 + side * 0.06)

        price_low = float(row['Low'])
        price_high = float(row['High'])
        
        if side == 1:
            if price_low  <= s['sl_price']: return 'SL', s['sl_price']
            if price_high >= s['tp_price']: return 'TP', s['tp_price']
        else:
            if price_high >= s['sl_price']: return 'SL', s['sl_price']
            if price_low  <= s['tp_price']: return 'TP', s['tp_price']

        return 'HOLD', None
