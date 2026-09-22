import numpy as np
import pandas as pd
import statsmodels.api as sm
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class RollingQuantileRegression(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Rolling Asymmetric Quantile Regression (Deep Learning / ML Factor).
    
    This Heavy ML factor fits a rolling Quantile Regression (q=0.05 and q=0.95) using statsmodels.
    It predicts the upper and lower tail boundaries of returns based on Volume and Volatility.
    When the lower tail risk boundary drastically compresses relative to the upper tail, 
    it indicates asymmetrical upside potential (a washout is complete).
    
    Due to extreme computational intensity, the regression models are only re-fitted 
    once every N bars (step_size) and forward-filled.
    """
    
    SIGNAL_PARAMS = frozenset({'lookback', 'step_size', 'q_lower', 'q_upper', 'asym_thresh'})
    
    OPTIMIZATION_RANGES = {
        'lookback': [50, 100, 250],
        'step_size': [12, 24], # Re-fit every 2 or 4 days to save compute
        'asym_thresh': [1.5, 2.0, 3.0],
        'sl_pct': [0.05, 0.10, 0.15],
        'tp_pct': [0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, lookback=100, step_size=12, q_lower=0.05, q_upper=0.95, asym_thresh=2.0, sl_pct=0.10, tp_pct=0.20, **kwargs):
        super().__init__(dfs, **kwargs)
        self.lookback = int(lookback)
        self.step_size = int(step_size)
        self.q_lower = float(q_lower)
        self.q_upper = float(q_upper)
        self.asym_thresh = float(asym_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            # Prepare features
            returns = df['Close'].pct_change().fillna(0)
            vol_delta = df['Volume'].pct_change().fillna(0)
            volatility = returns.rolling(20).std().fillna(0)
            
            # We want to predict returns using vol_delta and volatility
            X = pd.DataFrame({'const': 1, 'vol_delta': vol_delta, 'volatility': volatility})
            y = returns
            
            # Arrays to store predictions
            pred_lower = np.full(len(df), np.nan)
            pred_upper = np.full(len(df), np.nan)
            
            n = len(df)
            
            # Rolling fit with step_size to save compute
            for i in range(self.lookback, n, self.step_size):
                end_idx = i
                start_idx = i - self.lookback
                
                X_window = X.iloc[start_idx:end_idx]
                y_window = y.iloc[start_idx:end_idx]
                
                # Check for zero variance to avoid LinAlgError
                if y_window.std() < 1e-6:
                    continue
                    
                try:
                    # Fit 5th percentile (lower tail)
                    mod_lower = sm.QuantReg(y_window, X_window)
                    res_lower = mod_lower.fit(q=self.q_lower, max_iter=50, p_tol=1e-4)
                    
                    # Fit 95th percentile (upper tail)
                    mod_upper = sm.QuantReg(y_window, X_window)
                    res_upper = mod_upper.fit(q=self.q_upper, max_iter=50, p_tol=1e-4)
                    
                    # Predict for the next step_size bars using the latest coefficients
                    next_end = min(i + self.step_size, n)
                    X_next = X.iloc[i:next_end]
                    
                    pred_lower[i:next_end] = mod_lower.predict(res_lower.params, exog=X_next)
                    pred_upper[i:next_end] = mod_upper.predict(res_upper.params, exog=X_next)
                except Exception:
                    pass
            
            # Forward fill any gaps if prediction failed
            pred_lower = pd.Series(pred_lower, index=df.index).ffill()
            pred_upper = pd.Series(pred_upper, index=df.index).ffill()
            
            # Asymmetry calculation: Upper Tail upside vs Lower Tail downside
            # E.g. Upper Tail = +5%, Lower Tail = -1%
            # Asymmetry Ratio = 5 / 1 = 5.0 (highly skewed upside)
            # Add small epsilon to avoid div zero
            asym_ratio = pred_upper / (np.abs(pred_lower) + 1e-6)
            
            # Long condition: Upside tail is X times larger than downside tail risk
            long_cond = asym_ratio > self.asym_thresh
            
            # Short condition: Downside tail is X times larger than upside tail
            short_cond = (np.abs(pred_lower) / (pred_upper + 1e-6)) > self.asym_thresh
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond.fillna(False)] = 1
            signal[short_cond.fillna(False)] = -1
            
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
