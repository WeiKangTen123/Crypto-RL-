import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_zscore, calc_amihud_illiq

class MarketStressIndex(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: 5-Component Market Stress Index.
    
    This is an advanced Financial ML strategy that computes a composite 
    capitulation index using 5 Z-scored factors:
    1. RV (Realized Volatility): Rolling standard deviation of returns.
    2. Illiq (Amihud): Absolute return divided by dollar volume.
    3. Corr (Market Correlation): Rolling correlation to the portfolio mean return.
    4. Vol (Volume Surge): Volume divided by rolling mean volume.
    5. Trend (Price Momentum): Rolling percentage change.
    
    Stress Index = Z(RV) + Z(Illiq) + Z(Corr) + Z(Vol) - Z(Trend)
    
    An extremely high Stress Index represents a massive capitulation event 
    (high volatility, illiquid, highly correlated, high volume, dropping fast).
    This triggers a mean-reversion BUY.
    An extremely low Stress Index represents a calm, low-volume grind up.
    """
    
    SIGNAL_PARAMS = frozenset({'window', 'z_period', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'window': [10, 20, 30, 50],
        'z_period': [100, 250, 500],
        'long_thresh': [3.0, 5.0, 7.0, 9.0],
        'short_thresh': [-9.0, -7.0, -5.0, -3.0],
        'sl_pct': [0.05, 0.08, 0.12, 0.15],
        'tp_pct': [0.10, 0.15, 0.25, 0.40],
    }

    def __init__(self, dfs, window=20, z_period=250, long_thresh=5.0, short_thresh=-5.0, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.window = int(window)
        self.z_period = int(z_period)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        # 1. Calculate portfolio mean returns for the Correlation component
        returns_dict = {}
        for sym, df in self.dfs.items():
            returns_dict[sym] = df['Close'].pct_change(1).fillna(0)
            
        returns_df = pd.DataFrame(returns_dict)
        mean_returns = returns_df.mean(axis=1)
        
        for sym, df in self.dfs.items():
            ret = returns_df[sym]
            
            # RV (Realized Volatility)
            rv = ret.rolling(self.window).std().fillna(0)
            z_rv = calc_zscore(rv, self.z_period)
            
            # Illiquidity (Amihud)
            illiq = calc_amihud_illiq(df, self.window)
            z_illiq = calc_zscore(illiq, self.z_period)
            
            # Correlation to Mean Market Return
            corr = ret.rolling(self.window).corr(mean_returns).fillna(0)
            z_corr = calc_zscore(corr, self.z_period)
            
            # Volume Surge
            vol_mean = df['Volume'].rolling(self.window).mean()
            vol_surge = df['Volume'] / (vol_mean + 1e-8)
            z_vol = calc_zscore(vol_surge, self.z_period)
            
            # Trend
            trend = df['Close'].pct_change(self.window).fillna(0)
            z_trend = calc_zscore(trend, self.z_period)
            
            # Total Stress Index
            # If everything is panicking (high vol, illiquid, dumping), Stress will spike positive.
            stress = z_rv + z_illiq + z_corr + z_vol - z_trend
            
            # Clean up NaNs and reindex to match df
            stress = stress.fillna(0).loc[df.index]
            
            # Signals
            long_cond = stress > self.long_thresh
            short_cond = stress < self.short_thresh
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            signal_diff = np.diff(signal, prepend=0)
            entry_signals = np.zeros(len(df), dtype=int)
            entry_signals[(signal == 1) & (signal_diff > 0)] = 1
            entry_signals[(signal == -1) & (signal_diff < 0)] = -1
            
            self.dfs[sym]['signal'] = entry_signals
            
        return self.dfs

    def manage_trade(self, symbol: str, bar, qty: float, entry_price: float, entry_balance: float):
        action, exec_price = 'HOLD', None
        side = 1 if qty > 0 else -1
        
        if side == 1:
            sl_price = entry_price * (1 - self.sl_pct)
            tp_price = entry_price * (1 + self.tp_pct)
            
            if bar.Low <= sl_price:
                action, exec_price = 'SL', sl_price
            elif bar.High >= tp_price:
                action, exec_price = 'TP', tp_price
                
        else:
            sl_price = entry_price * (1 + self.sl_pct)
            tp_price = entry_price * (1 - self.tp_pct)
            
            if bar.High >= sl_price:
                action, exec_price = 'SL', sl_price
            elif bar.Low <= tp_price:
                action, exec_price = 'TP', tp_price
                
        return action, exec_price
