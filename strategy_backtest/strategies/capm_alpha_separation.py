import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_zscore

class CapmAlphaSeparation(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: CAPM Alpha Separation.
    
    This strategy uses the Capital Asset Pricing Model (CAPM) structure to separate 
    an asset's market beta (correlation to BTC) from its idiosyncratic Alpha.
    
    Expected_Return = Beta * BTC_Return
    Alpha_Residual = Actual_Return - Expected_Return
    
    If the rolling Alpha Residual surges positively (Z-score > threshold), it means 
    the coin is fundamentally outperforming the market risk-adjusted, indicating a 
    pure intrinsic breakout independent of macro BTC flows.
    """
    
    SIGNAL_PARAMS = frozenset({'beta_window', 'alpha_z_window', 'alpha_thresh'})
    
    OPTIMIZATION_RANGES = {
        'beta_window': [50, 100, 200, 300],
        'alpha_z_window': [20, 50, 100],
        'alpha_thresh': [1.5, 2.0, 2.5, 3.0],
        'sl_pct': [0.05, 0.08, 0.12],
        'tp_pct': [0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, beta_window=100, alpha_z_window=50, alpha_thresh=2.0, sl_pct=0.08, tp_pct=0.20, **kwargs):
        super().__init__(dfs, **kwargs)
        self.beta_window = int(beta_window)
        self.alpha_z_window = int(alpha_z_window)
        self.alpha_thresh = float(alpha_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        if 'BTC' not in self.dfs:
            return self.dfs
            
        btc_df = self.dfs['BTC']
        btc_ret = btc_df['Close'].pct_change(1).fillna(0)
        btc_var = btc_ret.rolling(self.beta_window).var().fillna(0)
        
        for sym, df in self.dfs.items():
            if sym == 'BTC':
                self.dfs[sym]['signal'] = np.zeros(len(df), dtype=int)
                continue
                
            coin_ret = df['Close'].pct_change(1).fillna(0)
            
            # Align BTC to coin index
            aligned_btc_ret = btc_ret.loc[df.index]
            aligned_btc_var = btc_var.loc[df.index]
            
            # Calculate Rolling Beta
            # Covariance(Coin, BTC) / Variance(BTC)
            covar = coin_ret.rolling(self.beta_window).cov(aligned_btc_ret).fillna(0)
            
            # Safe division
            beta = np.where(aligned_btc_var > 1e-8, covar / aligned_btc_var, 0.0)
            beta = pd.Series(beta, index=df.index)
            
            # Extract Alpha Residual
            expected_ret = beta * aligned_btc_ret
            alpha_residual = coin_ret - expected_ret
            
            # Calculate Z-Score of the Alpha Residual
            alpha_z = calc_zscore(alpha_residual, self.alpha_z_window)
            
            # Trend filter on the residual (is the alpha accelerating?)
            alpha_trend = alpha_residual.rolling(10).mean()
            
            # Long condition: Idiosyncratic Alpha breakout
            long_cond = (alpha_z > self.alpha_thresh) & (alpha_trend > 0)
            # Short condition: Idiosyncratic Alpha collapse
            short_cond = (alpha_z < -self.alpha_thresh) & (alpha_trend < 0)
            
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
