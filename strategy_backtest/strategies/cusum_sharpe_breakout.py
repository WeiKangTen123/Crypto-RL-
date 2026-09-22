import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class CusumSharpeBreakout(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: CUSUM Sharpe Breakout.
    
    This strategy calculates the rolling Sharpe Ratio of the asset and uses a 
    CUSUM (Cumulative Sum) structural break filter to detect regime shifts in 
    risk-adjusted returns.
    
    A positive CUSUM break on the Sharpe Ratio indicates the asset has entered a 
    low-volatility uptrend (an extremely high-quality trend).
    """
    
    SIGNAL_PARAMS = frozenset({'sharpe_window', 'cusum_thresh'})
    
    OPTIMIZATION_RANGES = {
        'sharpe_window': [20, 50, 100, 200],
        'cusum_thresh': [1.0, 2.0, 3.0, 5.0],
        'sl_pct': [0.05, 0.08, 0.10, 0.15],
        'tp_pct': [0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, sharpe_window=50, cusum_thresh=2.0, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.sharpe_window = int(sharpe_window)
        self.cusum_thresh = float(cusum_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            ret = df['Close'].pct_change(1).fillna(0)
            
            # Calculate rolling Sharpe Ratio (annualized approx for 4H)
            rolling_mean = ret.rolling(self.sharpe_window).mean()
            rolling_std = ret.rolling(self.sharpe_window).std()
            
            # 4H data has 6 bars a day, 365 days = 2190 bars a year
            annualized_factor = np.sqrt(2190)
            rolling_sharpe = np.where(rolling_std > 1e-8, (rolling_mean / rolling_std) * annualized_factor, 0.0)
            rolling_sharpe = pd.Series(rolling_sharpe, index=df.index).fillna(0)
            
            # Calculate CUSUM of Sharpe Ratio deviations
            sharpe_mean = rolling_sharpe.rolling(self.sharpe_window).mean().fillna(0)
            sharpe_dev = rolling_sharpe - sharpe_mean
            
            # CUSUM accumulation
            cusum_pos = np.zeros(len(df))
            cusum_neg = np.zeros(len(df))
            
            # We use a fast numpy loop to build the CUSUM
            # C_pos_t = max(0, C_pos_t-1 + dev_t)
            # C_neg_t = max(0, C_neg_t-1 - dev_t)
            dev_vals = sharpe_dev.values
            for i in range(1, len(df)):
                cusum_pos[i] = max(0, cusum_pos[i-1] + dev_vals[i])
                cusum_neg[i] = max(0, cusum_neg[i-1] - dev_vals[i])
                
            cusum_pos_s = pd.Series(cusum_pos, index=df.index)
            cusum_neg_s = pd.Series(cusum_neg, index=df.index)
            
            # Normalize CUSUM by rolling std of Sharpe to make threshold invariant
            sharpe_std = rolling_sharpe.rolling(self.sharpe_window).std().fillna(1.0)
            # Prevent div by zero
            sharpe_std = np.where(sharpe_std < 1e-8, 1.0, sharpe_std)
            
            norm_cusum_pos = cusum_pos_s / sharpe_std
            norm_cusum_neg = cusum_neg_s / sharpe_std
            
            # Long condition: Positive Sharpe breakout
            long_cond = norm_cusum_pos > self.cusum_thresh
            
            # Short condition: Negative Sharpe breakout (Regime collapse)
            short_cond = norm_cusum_neg > self.cusum_thresh
            
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
