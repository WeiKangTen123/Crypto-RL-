import pandas as pd
import numpy as np
import ta
from typing import Tuple, Optional
from strategy_backtest.base_strategy import BaseStrategy

class BBWVolatilityBreakoutStrategy(BaseStrategy):
    """
    Bollinger Band Width Volatility Breakout
    Detects low volatility squeeze via BBW and trades the breakout outside the Bands.
    """

    def __init__(self, df: pd.DataFrame, **kwargs):
        self.bb_period = kwargs.get('bb_period', 20)
        self.bb_std = kwargs.get('bb_std', 2.0)
        self.bbw_sma_period = kwargs.get('bbw_sma_period', 20)
        self.vol_sma_period = kwargs.get('vol_sma_period', 20)
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.05)
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.02)
        super().__init__(df, **kwargs)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df
        
        # Calculate Bollinger Bands using `ta`
        indicator_bb = ta.volatility.BollingerBands(close=df["Close"], window=self.bb_period, window_dev=self.bb_std)
        
        df['BBL'] = indicator_bb.bollinger_lband()
        df['BBM'] = indicator_bb.bollinger_mavg()
        df['BBU'] = indicator_bb.bollinger_hband()
        df['BBW'] = indicator_bb.bollinger_wband() / 100.0  # normalize
        
        # BBW SMA
        df['BBW_SMA'] = df['BBW'].rolling(window=self.bbw_sma_period).mean()
        
        # Volume SMA
        df['Vol_SMA'] = df['Volume'].rolling(window=self.vol_sma_period).mean()

        df['signal'] = 0
        
        # Squeeze condition
        squeeze = df['BBW'] < df['BBW_SMA']
        prev_squeeze = squeeze.shift(1).fillna(False)

        # Breakout conditions
        long_breakout = (df['Close'] > df['BBU']) & prev_squeeze & (df['Volume'] > df['Vol_SMA'])
        short_breakout = (df['Close'] < df['BBL']) & prev_squeeze & (df['Volume'] > df['Vol_SMA'])

        df.loc[long_breakout, 'signal'] = 1
        df.loc[short_breakout, 'signal'] = -1
        
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        
        if position > 0:
            sl = entry_price * (1 - self.stop_loss_pct)
            tp = entry_price * (1 + self.take_profit_pct)
            if row['Low']  <= sl: return 'SL', sl

            if row['High'] >= tp: return 'TP', tp
            if row['Close'] < row['BBM']:
                return 'EXIT', row['Close']

        elif position < 0:
            sl = entry_price * (1 + self.stop_loss_pct)
            tp = entry_price * (1 - self.take_profit_pct)
            if row['High'] >= sl: return 'SL', sl

            if row['Low']  <= tp: return 'TP', tp
            if row['Close'] > row['BBM']:
                return 'EXIT', row['Close']
                
        return 'HOLD', None
