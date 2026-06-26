import pandas as pd
import numpy as np
import ta
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy

class DynamicSwingAnchoredVWAPStrategy(BaseStrategy):
    """
    Dynamic Swing Anchored VWAP
    Anchors VWAP to recent swing highs/lows and trades breakouts.
    """

    OPTIMIZATION_RANGES = {
        'swing_lookback':    (5,   50),
        'atr_period':        (5,   30),
        'sl_atr_multiplier': (0.5,  4.0),
        'tp_rr_ratio':       (1.0,  8.0),
        'vol_sma_period':    (5,   50),
        'breakout_mode':     ['VOLUME_CONFIRMED', 'PLAIN'],
    }

    SIGNAL_PARAMS = frozenset({'swing_lookback', 'vol_sma_period', 'breakout_mode'})

    def __init__(self, df: pd.DataFrame, **kwargs):
        self.swing_lookback = kwargs.get('swing_lookback', 20)
        self.atr_period = kwargs.get('atr_period', 14)
        self.sl_atr_multiplier = kwargs.get('sl_atr_multiplier', 2.0)
        self.tp_rr_ratio = kwargs.get('tp_rr_ratio', 3.0)
        self.vol_sma_period = kwargs.get('vol_sma_period', 20)
        self.breakout_mode = kwargs.get('breakout_mode', 'VOLUME_CONFIRMED')
        super().__init__(df, **kwargs)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        volume = df['Volume'].values
        typical_price = (high + low + close) / 3.0
        
        # ATR and Vol SMA
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=self.atr_period)
        df['Vol_SMA'] = df['Volume'].rolling(window=self.vol_sma_period).mean()
        
        n = len(df)
        signals = np.zeros(n, dtype=int)
        avwap_val = np.full(n, np.nan)
        anchor_types = np.zeros(n, dtype=int) # 1 for low anchor, -1 for high anchor
        
        # We need to detect swing highs and lows and anchor VWAP.
        # Swing High: Highest high in a window. Swing Low: Lowest low in a window.
        
        current_anchor_idx = 0
        current_anchor_type = 0 # 1=low, -1=high
        
        cum_vol = 0.0
        cum_tp_vol = 0.0
        
        for i in range(self.swing_lookback * 2, n):
            # Check if i - swing_lookback is a swing pivot
            window_highs = high[i - 2*self.swing_lookback : i]
            window_lows = low[i - 2*self.swing_lookback : i]
            
            mid_idx_local = self.swing_lookback
            
            is_swing_high = True
            is_swing_low = True
            
            mid_high = window_highs[mid_idx_local]
            mid_low = window_lows[mid_idx_local]
            
            for j in range(len(window_highs)):
                if j == mid_idx_local:
                    continue
                if window_highs[j] >= mid_high:
                    is_swing_high = False
                if window_lows[j] <= mid_low:
                    is_swing_low = False
                    
            if is_swing_high:
                # new anchor is high (potential short)
                current_anchor_idx = i - self.swing_lookback
                current_anchor_type = -1
                cum_vol = 0.0
                cum_tp_vol = 0.0
                
                # backfill since the new anchor
                for k in range(current_anchor_idx, i):
                    cum_vol += volume[k]
                    cum_tp_vol += typical_price[k] * volume[k]
            elif is_swing_low:
                # new anchor is low (potential long)
                current_anchor_idx = i - self.swing_lookback
                current_anchor_type = 1
                cum_vol = 0.0
                cum_tp_vol = 0.0
                
                for k in range(current_anchor_idx, i):
                    cum_vol += volume[k]
                    cum_tp_vol += typical_price[k] * volume[k]
                    
            # Accumulate current bar
            if current_anchor_idx > 0:
                cum_vol += volume[i]
                cum_tp_vol += typical_price[i] * volume[i]
                if cum_vol > 0:
                    avwap_val[i] = cum_tp_vol / cum_vol
                anchor_types[i] = current_anchor_type
                
                # Signal Generation
                vol_ok = (self.breakout_mode == 'PLAIN') or (volume[i] > df['Vol_SMA'].iloc[i])

                # Long: Price breaks above AVWAP anchored at recent swing low.
                if current_anchor_type == 1 and close[i-1] < avwap_val[i-1] and close[i] > avwap_val[i] and vol_ok:
                    signals[i] = 1

                # Short: Price breaks below AVWAP anchored at recent swing high.
                if current_anchor_type == -1 and close[i-1] > avwap_val[i-1] and close[i] < avwap_val[i] and vol_ok:
                    signals[i] = -1

        df['signal'] = signals
        df['AVWAP'] = avwap_val
        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        atr = row['ATR'] if not pd.isna(row['ATR']) else entry_price * 0.02
        sl_dist = atr * self.sl_atr_multiplier
        tp_dist = sl_dist * self.tp_rr_ratio
        
        if position > 0:
            sl = entry_price - sl_dist
            tp = entry_price + tp_dist
            if row['Low']  <= sl: return 'SL', sl

            if row['High'] >= tp: return 'TP', tp
            if row['Close'] < row['AVWAP']:
                return 'EXIT', row['Close']

        elif position < 0:
            sl = entry_price + sl_dist
            tp = entry_price - tp_dist
            if row['High'] >= sl: return 'SL', sl

            if row['Low']  <= tp: return 'TP', tp
            if row['Close'] > row['AVWAP']:
                return 'EXIT', row['Close']
                
        return 'HOLD', None
