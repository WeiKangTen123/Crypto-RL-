import pandas as pd
import numpy as np
import talib
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy

class TripleConfirmFVMAStrategy(BaseStrategy):
    """
    Triple Confirmation FVMA ZeroLag MACD Strategy.
    mode='strict'  — all 3 conditions must agree: SuperTrend + FVMA + ZMACD cross
    mode='relaxed' — 2-of-3: SuperTrend + ZMACD cross (FVMA not required)
    mode='macd_st' — SuperTrend direction filter + ZMACD cross only (no FVMA)
    """

    OPTIMIZATION_RANGES = {
        'supertrend_length':     (5,  30),
        'supertrend_multiplier': (1.0, 5.0),
        'fvma_period':           (3,  20),
        'macd_fast':             (3,  20),
        'macd_slow':             (20, 80),  # raised floor — need clear separation from fast
        'macd_signal':           (3,  15),
        'tp_atr_mult':           (1.5, 8.0),  # raised floor — 1.0× ATR TP too tight
        'sl_atr_mult':           (0.5, 3.0),
        'mode':                  ['strict', 'relaxed', 'macd_st'],
    }

    @classmethod
    def validate_params(cls, params):
        # MACD fast must be meaningfully below slow
        fast = params.get('macd_fast', 12)
        slow = params.get('macd_slow', 26)
        if slow - fast < 8:
            return False
        # TP must exceed SL ratio for positive expectancy
        tp = params.get('tp_atr_mult', 3.0)
        sl = params.get('sl_atr_mult', 1.5)
        if tp < sl:
            return False
        return True

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.supertrend_length     = kwargs.get('supertrend_length', 10)
        self.supertrend_multiplier = kwargs.get('supertrend_multiplier', 3.0)
        self.fvma_period           = kwargs.get('fvma_period', 5)
        self.macd_fast             = kwargs.get('macd_fast', 12)
        self.macd_slow             = kwargs.get('macd_slow', 26)
        self.macd_signal           = kwargs.get('macd_signal', 9)
        self.tp_atr_mult           = kwargs.get('tp_atr_mult', 3.0)
        self.sl_atr_mult           = kwargs.get('sl_atr_mult', 1.5)
        self.mode                  = kwargs.get('mode', 'strict')

    def _zero_lag_macd(self, close: pd.Series) -> Tuple[pd.Series, pd.Series]:
        ema1_fast = talib.EMA(close, timeperiod=self.macd_fast)
        ema2_fast = talib.EMA(ema1_fast, timeperiod=self.macd_fast)
        dema_fast = 2 * ema1_fast - ema2_fast

        ema1_slow = talib.EMA(close, timeperiod=self.macd_slow)
        ema2_slow = talib.EMA(ema1_slow, timeperiod=self.macd_slow)
        dema_slow = 2 * ema1_slow - ema2_slow

        zmacd = dema_fast - dema_slow
        signal = talib.EMA(zmacd, timeperiod=self.macd_signal)
        return zmacd, signal

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # Supertrend Calculation
        hl2 = (df['High'] + df['Low']) / 2
        atr = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.supertrend_length)
        df['atr'] = atr
        
        basic_ub = hl2 + (self.supertrend_multiplier * atr)
        basic_lb = hl2 - (self.supertrend_multiplier * atr)
        
        final_ub = np.zeros(len(df))
        final_lb = np.zeros(len(df))
        supertrend = np.zeros(len(df))
        supertrend_dir = np.zeros(len(df))
        
        # Find first non-NaN index
        first_valid = basic_ub.first_valid_index()
        if first_valid is None:
            first_idx = 0
        else:
            first_idx = df.index.get_loc(first_valid)

        if first_idx < len(df):
            final_ub[first_idx] = basic_ub.iloc[first_idx]
            final_lb[first_idx] = basic_lb.iloc[first_idx]
            supertrend[first_idx] = final_ub[first_idx]
            supertrend_dir[first_idx] = -1

        for i in range(first_idx + 1, len(df)):
            supertrend_dir[i] = supertrend_dir[i-1]
            
            final_ub[i] = basic_ub.iloc[i] if basic_ub.iloc[i] < final_ub[i-1] or df['Close'].iloc[i-1] > final_ub[i-1] else final_ub[i-1]
            final_lb[i] = basic_lb.iloc[i] if basic_lb.iloc[i] > final_lb[i-1] or df['Close'].iloc[i-1] < final_lb[i-1] else final_lb[i-1]
            
            if supertrend_dir[i-1] == 1 and df['Close'].iloc[i] < final_lb[i]:
                supertrend_dir[i] = -1
            elif supertrend_dir[i-1] == -1 and df['Close'].iloc[i] > final_ub[i]:
                supertrend_dir[i] = 1
                
            if supertrend_dir[i] == 1:
                supertrend[i] = final_lb[i]
            else:
                supertrend[i] = final_ub[i]
                
        df['supertrend_dir'] = supertrend_dir

        # 2. FVMA (Fast EMA)
        df['fvma'] = talib.EMA(df['Close'], timeperiod=self.fvma_period)

        # 3. Zero Lag MACD
        zmacd, zmacd_signal = self._zero_lag_macd(df['Close'])
        df['zmacd'] = zmacd
        df['zmacd_signal'] = zmacd_signal

        df['signal'] = 0

        # Conditions
        zmacd_cross_up = (df['zmacd'] > df['zmacd_signal']) & (df['zmacd'].shift(1) <= df['zmacd_signal'].shift(1))
        zmacd_cross_down = (df['zmacd'] < df['zmacd_signal']) & (df['zmacd'].shift(1) >= df['zmacd_signal'].shift(1))

        if self.mode == 'relaxed':
            # 2-of-3: SuperTrend + ZMACD cross (FVMA not required)
            bullish_cond = (df['supertrend_dir'] == 1) & zmacd_cross_up
            bearish_cond = (df['supertrend_dir'] == -1) & zmacd_cross_down
        elif self.mode == 'macd_st':
            # SuperTrend direction only + ZMACD cross
            bullish_cond = (df['supertrend_dir'] == 1) & zmacd_cross_up
            bearish_cond = (df['supertrend_dir'] == -1) & zmacd_cross_down
        else:
            # strict (default): all 3 must agree
            bullish_cond = (df['supertrend_dir'] == 1) & (df['Close'] > df['fvma']) & zmacd_cross_up
            bearish_cond = (df['supertrend_dir'] == -1) & (df['Close'] < df['fvma']) & zmacd_cross_down

        df.loc[bullish_cond, 'signal'] = 1
        df.loc[bearish_cond, 'signal'] = -1

        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        if pd.isna(getattr(row, 'atr', np.nan)):
            return 'HOLD', None

        # Fixed ATR-based TP/SL from entry
        if position > 0:
            tp_price = entry_price + (row.atr * self.tp_atr_mult)
            sl_price = entry_price - (row.atr * self.sl_atr_mult)
            if row.Low  <= sl_price: return 'SL', sl_price
            if row.High >= tp_price: return 'TP', tp_price
            # Dynamic exit on ZMACD cross down
            if row.zmacd < row.zmacd_signal and row.signal != 1:
                return 'EXIT', row.Close

        elif position < 0:
            tp_price = entry_price - (row.atr * self.tp_atr_mult)
            sl_price = entry_price + (row.atr * self.sl_atr_mult)
            if row.High >= sl_price: return 'SL', sl_price
            if row.Low  <= tp_price: return 'TP', tp_price
            # Dynamic exit on ZMACD cross up
            if row.zmacd > row.zmacd_signal and row.signal != -1:
                return 'EXIT', row.Close

        return 'HOLD', None
