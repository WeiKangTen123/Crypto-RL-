import pandas as pd
import numpy as np
import talib
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import (
    calc_spot_obi,
    calc_depth_imbalance,
    calc_linear_regression_slope
)

class MicrostructureEnsembleStrategy(BaseStrategy):
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    SIGNAL_PARAMS = frozenset({
        'fr_trend_period', 'obi_threshold', 'depth_perc',
        'zscore_thresh', 'tp_multiplier', 'sl_multiplier'
    })

    OPTIMIZATION_RANGES = {
        'fr_trend_period': (8, 24),
        'obi_threshold': (0.1, 0.5),
        'depth_perc': (0.8, 0.95),
        'zscore_thresh': (1.5, 3.0),
        'tp_multiplier': (2.0, 8.0),
        'sl_multiplier': (0.5, 3.0)
    }

    def __init__(self, df: pd.DataFrame,
                 fr_trend_period: int = 15,
                 obi_threshold: float = 0.2727,
                 depth_perc: float = 0.8328,
                 zscore_thresh: float = 2.7932,
                 tp_multiplier: float = 4.1907,
                 sl_multiplier: float = 2.9545,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.fr_trend_period = int(fr_trend_period)
        self.obi_threshold = float(obi_threshold)
        self.depth_perc = float(depth_perc)
        self.zscore_thresh = float(zscore_thresh)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)

    def generate_signals(self):
        df = self.df.copy()

        # FRDS Logic
        df['price_trend'] = calc_linear_regression_slope(df['Close'], self.fr_trend_period)
        if 'funding_rate' in df.columns:
            df['fr_trend'] = calc_linear_regression_slope(df['funding_rate'], self.fr_trend_period)
            roll_mean = df['funding_rate'].rolling(84).mean()
            roll_std = df['funding_rate'].rolling(84).std()
            df['fr_zscore'] = (df['funding_rate'] - roll_mean) / (roll_std + 1e-10)
        else:
            df['fr_trend'] = 0
            df['fr_zscore'] = 0
            
        df['spot_obi'] = calc_spot_obi(df)

        # LER Logic
        df['depth_imbalance'] = calc_depth_imbalance(df)
        df['depth_90'] = df['depth_imbalance'].rolling(100).quantile(self.depth_perc)
        df['depth_10'] = df['depth_imbalance'].rolling(100).quantile(1.0 - self.depth_perc)
        upper, middle, lower = talib.BBANDS(df['Close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        
        # Scoring: Score 1 point for each condition met
        df['frds_long'] = (df['price_trend'] > 0) & (df['fr_trend'] < 0) & (df['spot_obi'] > 0)
        df['frds_short'] = (df['price_trend'] < 0) & (df['fr_trend'] > 0) & (df['spot_obi'] < 0)

        df['ler_long'] = (df['Low'] <= lower) & (df['depth_imbalance'] < df['depth_10'])
        df['ler_short'] = (df['High'] >= upper) & (df['depth_imbalance'] > df['depth_90'])

        df['efr_long'] = (df['fr_zscore'] < -self.zscore_thresh) & (df['spot_obi'] > self.obi_threshold)
        df['efr_short'] = (df['fr_zscore'] > self.zscore_thresh) & (df['spot_obi'] < -self.obi_threshold)

        # We require at least 2 out of the 3 Microstructure factors to align for an entry
        long_score = df['frds_long'].astype(int) + df['ler_long'].astype(int) + df['efr_long'].astype(int)
        short_score = df['frds_short'].astype(int) + df['ler_short'].astype(int) + df['efr_short'].astype(int)

        df['signal'] = 0
        df.loc[long_score >= 2, 'signal'] = 1
        df.loc[short_score >= 2, 'signal'] = -1
        
        # Exit params
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        self.df = df
        return df

    def manage_trade(self, row, qty, entry_price, entry_equity):
        if qty > 0:
            tp = entry_price + (row['atr'] * self.tp_multiplier)
            sl = entry_price - (row['atr'] * self.sl_multiplier)
            if row['Low']  <= sl: return 'SL', sl

            if row['High'] >= tp: return 'TP', tp
        elif qty < 0:
            tp = entry_price - (row['atr'] * self.tp_multiplier)
            sl = entry_price + (row['atr'] * self.sl_multiplier)
            if row['High'] >= sl: return 'SL', sl

            if row['Low']  <= tp: return 'TP', tp
        return 'HOLD', None
