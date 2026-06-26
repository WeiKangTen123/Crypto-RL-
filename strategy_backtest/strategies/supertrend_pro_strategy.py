import pandas as pd
import numpy as np
import talib
from typing import Optional, Tuple

from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_adx, calc_bb_kc_squeeze, calc_chandelier_exit

class SupertrendProStrategy(BaseStrategy):
    """
    Supertrend Pro Volatility Breakout with ADX and Squeeze filters, and Chandelier Exit.
    """

    # Hard bounds for Optuna — multiplier below 0.5 creates degenerate near-zero bands.
    OPTIMIZATION_RANGES = {
        'multiplier':    (0.5, 5.0),
        'kc_multiplier': (0.5, 3.0),
    }

    @staticmethod
    def validate_params(params: dict) -> bool:
        if params.get('multiplier', 1.0) < 0.5:
            return False
        return True

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.atr_period = kwargs.get('atr_period', 10)
        self.multiplier = kwargs.get('multiplier', 3.0)
        self.adx_period = kwargs.get('adx_period', 14)
        self.adx_threshold = kwargs.get('adx_threshold', 25)
        self.bb_period = kwargs.get('bb_period', 20)
        self.bb_std = kwargs.get('bb_std', 2.0)
        self.kc_multiplier = kwargs.get('kc_multiplier', 1.5)
        self.chandelier_atr_period = kwargs.get('chandelier_atr_period', 22)
        self.chandelier_multiplier = kwargs.get('chandelier_multiplier', 3.0)
        self.long_only = kwargs.get('long_only', True) # For Chandelier Exit

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()

        # 1. Indicators
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.atr_period)
        df['adx'] = calc_adx(df, period=self.adx_period)
        
        # Bollinger Bands for Squeeze calculation
        upper_bb, mid_bb, lower_bb = talib.BBANDS(df['Close'], timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std)
        # Keltner Channels for Squeeze calculation
        kc_atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.bb_period) # Use BB period for KC ATR
        mid_kc = talib.EMA(df['Close'], timeperiod=self.bb_period)
        upper_kc = mid_kc + (kc_atr * self.kc_multiplier)
        lower_kc = mid_kc - (kc_atr * self.kc_multiplier)

        # Squeeze detection: BB inside KC
        df['squeeze_on'] = (lower_bb > lower_kc) & (upper_bb < upper_kc)

        # Fill NaNs
        df = df.ffill().bfill()
        
        # Chandelier Exit
        df['long_exit'], df['short_exit'] = calc_chandelier_exit(df, self.chandelier_atr_period, self.chandelier_multiplier, self.long_only)

        # 2. Supertrend Calculation (basic, will be filtered later)
        hl2 = (df['High'] + df['Low']) / 2
        df['basic_ub'] = hl2 + (self.multiplier * df['atr'])
        df['basic_lb'] = hl2 - (self.multiplier * df['atr'])
        
        # Initialize Supertrend and direction
        final_ub = pd.Series(0.0, index=df.index)
        final_lb = pd.Series(0.0, index=df.index)
        supertrend = pd.Series(0.0, index=df.index)
        supertrend_direction = pd.Series(1, index=df.index) # 1 for Long, -1 for Short

        for i in range(1, len(df)):
            # Final Upper Band
            if df['basic_ub'].iloc[i] < final_ub.iloc[i-1] or df['Close'].iloc[i-1] > final_ub.iloc[i-1]:
                final_ub.iloc[i] = df['basic_ub'].iloc[i]
            else:
                final_ub.iloc[i] = final_ub.iloc[i-1]
            
            # Final Lower Band
            if df['basic_lb'].iloc[i] > final_lb.iloc[i-1] or df['Close'].iloc[i-1] < final_lb.iloc[i-1]:
                final_lb.iloc[i] = df['basic_lb'].iloc[i]
            else:
                final_lb.iloc[i] = final_lb.iloc[i-1]
                
            # Supertrend
            if supertrend.iloc[i-1] == final_ub.iloc[i-1] and df['Close'].iloc[i] <= final_ub.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
                supertrend_direction.iloc[i] = -1
            elif supertrend.iloc[i-1] == final_ub.iloc[i-1] and df['Close'].iloc[i] > final_ub.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
                supertrend_direction.iloc[i] = 1
            elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and df['Close'].iloc[i] >= final_lb.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
                supertrend_direction.iloc[i] = 1
            elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and df['Close'].iloc[i] < final_lb.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
                supertrend_direction.iloc[i] = -1
        
        df['supertrend'] = supertrend
        df['supertrend_direction'] = supertrend_direction
        
        # 3. Generate Signals with Filters
        # Entry Conditions:
        # 1. Supertrend flips up (direction changes from -1 to 1)
        # 2. ADX > adx_threshold (trending market)
        # 3. NOT in a squeeze (Bollinger Bands NOT inside Keltner Channels)
        long_entries = ((df['supertrend_direction'].shift(1) == -1) &
                        (df['supertrend_direction'] == 1) &
                        (df['adx'] > self.adx_threshold) &
                        (~df['squeeze_on']))

        signals = np.zeros(len(df), dtype=int)
        signals[long_entries.values] = 1
        df['signal'] = signals

        self._long_exit_arr = df['long_exit'].values
        # Store for fast lookup
        self._bar_index_map = {idx: i for i, idx in enumerate(df.index)}
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0.0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None

        side = int(np.sign(position))
        bar_idx = self._bar_index_map.get(row.name, -1)

        # We only have long trades in this strategy
        if side == 1:
            long_exit_val = float(self._long_exit_arr[bar_idx]) if bar_idx >= 0 else float(row['Close'])
            # Use Low for intrabar wick detection; fill at chandelier level, not Close
            if float(row['Low']) < long_exit_val:
                return 'EXIT', long_exit_val

        return 'HOLD', None