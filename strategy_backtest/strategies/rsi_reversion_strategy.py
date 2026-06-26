import pandas as pd
import talib
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_rsi

class RSIReversionStrategy(BaseStrategy):
    """
    RSI Reversion Strategy: Enters long when RSI is oversold, short when overbought.
    mode='off'    — trade both directions with no trend filter (original)
    mode='ema200' — only long above EMA200, only short below EMA200
    mode='atr_sl' — same as off but with ATR-based stop loss instead of RSI exit
    """

    OPTIMIZATION_RANGES = {
        'rsi_period':    (7,  21),
        'rsi_oversold':  (20, 65),   # fully open — let Optuna find the true optimum
        'rsi_overbought':(35, 80),
        'ema_period':    (50, 300),
        'atr_period':    (5,  21),
        'atr_multiplier_sl': (0.5, 4.0),  # expanded floor
        'mode':          ['off', 'ema200', 'atr_sl'],
    }

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.rsi_period        = kwargs.get('rsi_period', 14)
        self.rsi_oversold      = kwargs.get('rsi_oversold', 30)
        self.rsi_overbought    = kwargs.get('rsi_overbought', 70)
        self.ema_period        = kwargs.get('ema_period', 200)
        self.atr_period        = kwargs.get('atr_period', 14)
        self.atr_multiplier_sl = kwargs.get('atr_multiplier_sl', 2.0)
        self.mode              = kwargs.get('mode', 'off')

    def generate_signals(self) -> pd.DataFrame:
        self.df['rsi'] = calc_rsi(self.df['Close'], period=self.rsi_period)
        self.df['atr'] = talib.ATR(
            self.df['High'], self.df['Low'], self.df['Close'],
            timeperiod=self.atr_period
        )

        self.df['signal'] = 0
        long_mask  = self.df['rsi'] < self.rsi_oversold
        short_mask = self.df['rsi'] > self.rsi_overbought

        if self.mode == 'ema200':
            ema = talib.EMA(self.df['Close'], timeperiod=self.ema_period)
            self.df['ema_trend'] = ema
            long_mask  = long_mask  & (self.df['Close'] > ema)
            short_mask = short_mask & (self.df['Close'] < ema)

        self.df.loc[long_mask,  'signal'] = 1
        self.df.loc[short_mask, 'signal'] = -1
        return self.df

    def manage_trade(self, row, position, entry_price, wallet=0):
        rsi = getattr(row, 'rsi', None)
        atr = getattr(row, 'atr', None)

        if self.mode == 'atr_sl':
            if position > 0 and atr:
                sl = entry_price - self.atr_multiplier_sl * atr
                if float(row['Low']) < sl:
                    return 'SL', sl
                if rsi and rsi > self.rsi_overbought:
                    return 'EXIT', None
            elif position < 0 and atr:
                sl = entry_price + self.atr_multiplier_sl * atr
                if float(row['High']) > sl:
                    return 'SL', sl
                if rsi and rsi < self.rsi_oversold:
                    return 'EXIT', None
        else:
            if position > 0 and rsi and rsi > self.rsi_overbought:
                return 'EXIT', None
            elif position < 0 and rsi and rsi < self.rsi_oversold:
                return 'EXIT', None

        return 'HOLD', None
