import pandas as pd
import numpy as np
from strategy_backtest.base_strategy import BaseStrategy

class T3NexusStiffStrategy(BaseStrategy):
    """
    T3 Nexus + Stiff Surge Strategy
    Combines T3 Moving Average, Waddah Attar Explosion, and Stiff Filter.
    """
    SIGNAL_PARAMS = frozenset({
        't3_length', 't3_vf', 'wae_sensitivity', 'wae_fast_len',
        'wae_slow_len', 'wae_bb_len', 'wae_bb_mult', 'wae_deadzone',
        'stiff_len', 'stiff_threshold'
    })

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        # T3 Params
        self.t3_length = getattr(self, 't3_length', 25)
        self.t3_vf = getattr(self, 't3_vf', 0.7)
        
        # WAE Params
        self.wae_sensitivity = getattr(self, 'wae_sensitivity', 150)
        self.wae_fast_len = getattr(self, 'wae_fast_len', 20)
        self.wae_slow_len = getattr(self, 'wae_slow_len', 40)
        self.wae_bb_len = getattr(self, 'wae_bb_len', 20)
        self.wae_bb_mult = getattr(self, 'wae_bb_mult', 2.0)
        self.wae_deadzone = getattr(self, 'wae_deadzone', 20)
        
        # Stiff Params
        self.stiff_len = getattr(self, 'stiff_len', 60)
        self.stiff_threshold = getattr(self, 'stiff_threshold', 0.9) # 90% of bars above MA

        # Risk Params (Handled by RiskManager but stored here for reference)
        self.stop_loss_pct = getattr(self, 'stop_loss_pct', 0.02)
        self.take_profit_pct = getattr(self, 'take_profit_pct', 0.04)

    def _t3(self, series, length, vf):
        a = vf
        e1 = series.ewm(span=length, adjust=False).mean()
        e2 = e1.ewm(span=length, adjust=False).mean()
        e3 = e2.ewm(span=length, adjust=False).mean()
        e4 = e3.ewm(span=length, adjust=False).mean()
        e5 = e4.ewm(span=length, adjust=False).mean()
        e6 = e5.ewm(span=length, adjust=False).mean()
        c1 = -a**3
        c2 = 3*a**2 + 3*a**3
        c3 = -6*a**2 - 3*a - 3*a**3
        c4 = 1 + 3*a + a**3 + 3*a**2
        return c1*e6 + c2*e5 + c3*e4 + c4*e3

    def generate_signals(self) -> pd.DataFrame:
        # 1. T3 Nexus
        self.df['t3'] = self._t3(self.df['Close'], self.t3_length, self.t3_vf)
        
        # 2. Waddah Attar Explosion
        self.df['wae_trend'] = (self.df['Close'].ewm(span=self.wae_fast_len, adjust=False).mean() - 
                                self.df['Close'].ewm(span=self.wae_slow_len, adjust=False).mean()) * self.wae_sensitivity
        
        rolling_mean = self.df['Close'].rolling(self.wae_bb_len).mean()
        rolling_std = self.df['Close'].rolling(self.wae_bb_len).std()
        self.df['wae_explosion'] = (rolling_mean + self.wae_bb_mult * rolling_std) - \
                                   (rolling_mean - self.wae_bb_mult * rolling_std)
        
        # 3. Stiff Filter
        ma_stiff = self.df['Close'].ewm(span=self.stiff_len, adjust=False).mean()
        self.df['stiff'] = (self.df['Close'] > ma_stiff).rolling(self.stiff_len).sum() / self.stiff_len
        
        # Entry Logic
        self.df['signal'] = 0
        
        # Long Conditions
        long_cond = (
            (self.df['Close'] > self.df['t3']) & 
            (self.df['wae_trend'] > 0) & 
            (self.df['wae_trend'] > self.df['wae_trend'].shift(1)) & 
            (self.df['wae_trend'] > self.df['wae_explosion']) & 
            (self.df['wae_trend'] > self.wae_deadzone) &
            (self.df['stiff'] >= self.stiff_threshold)
        )
        
        # Short Conditions
        short_cond = (
            (self.df['Close'] < self.df['t3']) & 
            (self.df['wae_trend'] < 0) & 
            (self.df['wae_trend'] < self.df['wae_trend'].shift(1)) & 
            (abs(self.df['wae_trend']) > self.df['wae_explosion']) & 
            (abs(self.df['wae_trend']) > self.wae_deadzone) &
            ((1 - self.df['stiff']) >= self.stiff_threshold) # Stiff for short: 90% of bars BELOW MA
        )
        
        self.df.loc[long_cond, 'signal'] = 1
        self.df.loc[short_cond, 'signal'] = -1
        
        # Only take the first signal in a series
        # Note: In this engine, 'signal' usually means 'try to enter'. 
        # The backtester handles whether we are already in a position.
        
        return self.df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0):
        # Exit on T3 cross
        if position > 0:
            if row['Close'] < row['t3']:
                return 'EXIT', None
        elif position < 0:
            if row['Close'] > row['t3']:
                return 'EXIT', None
                
        return 'HOLD', None
