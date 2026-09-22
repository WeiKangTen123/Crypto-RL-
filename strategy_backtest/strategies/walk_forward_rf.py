import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_zscore, calc_amihud_illiq, calc_rsi

class WalkForwardRF(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Walk-Forward Random Forest.
    
    This is an advanced Deep Learning / Machine Learning proxy strategy.
    Instead of using static linear weights (like WorldQuant Alphas), this strategy 
    trains a Random Forest classifier dynamically on a rolling window of recent data 
    and predicts the forward bar direction for the next out-of-sample block.
    
    Features:
    - Multi-timeframe returns (1-bar, 4-bar, 24-bar)
    - RSI (Momentum)
    - Volume Z-Score (Activity)
    - Amihud Illiquidity (Market Depth)
    
    The model retrains every `retrain_interval` bars, learning the shifting 
    market regimes (SHAP proxy) and preventing long-term decay.
    """
    
    SIGNAL_PARAMS = frozenset({'train_window', 'retrain_interval', 'n_estimators', 'max_depth', 'prob_thresh'})
    
    OPTIMIZATION_RANGES = {
        'train_window': [500, 1000, 2000],
        'retrain_interval': [100, 200, 400],
        'n_estimators': [10, 20, 30],
        'max_depth': [3, 5, 7],
        'prob_thresh': [0.55, 0.60, 0.65],
        'sl_pct': [0.05, 0.08, 0.12, 0.15],
        'tp_pct': [0.10, 0.15, 0.20, 0.30],
    }

    def __init__(self, dfs, train_window=1000, retrain_interval=200, n_estimators=20, max_depth=5, prob_thresh=0.60, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.train_window = int(train_window)
        self.retrain_interval = int(retrain_interval)
        self.n_estimators = int(n_estimators)
        self.max_depth = int(max_depth)
        self.prob_thresh = float(prob_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            # 1. Feature Engineering
            features = pd.DataFrame(index=df.index)
            features['ret_1'] = df['Close'].pct_change(1)
            features['ret_4'] = df['Close'].pct_change(4)
            features['ret_24'] = df['Close'].pct_change(24)
            features['rsi_14'] = calc_rsi(df['Close'], 14) / 100.0 # Normalize 0-1
            
            vol_mean = df['Volume'].rolling(20).mean()
            features['vol_z'] = calc_zscore(df['Volume'] / (vol_mean + 1e-8), 100)
            features['illiq'] = calc_zscore(calc_amihud_illiq(df, 20), 100)
            
            # Forward Target (1 if next bar goes up, 0 if down)
            target = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
            
            # Clean NaNs (pad with 0 to maintain length)
            features = features.fillna(0)
            
            signal_array = np.zeros(len(df), dtype=int)
            
            # 2. Walk-Forward Training Loop
            for i in range(self.train_window, len(df), self.retrain_interval):
                train_start = i - self.train_window
                train_end = i
                test_start = i
                test_end = min(i + self.retrain_interval, len(df))
                
                # Extract Data
                train_X = features.iloc[train_start:train_end].values
                train_y = target[train_start:train_end]
                test_X = features.iloc[test_start:test_end].values
                
                # If target only has one class (extreme anomaly), skip
                if len(np.unique(train_y)) < 2:
                    continue
                    
                # Train Model
                model = RandomForestClassifier(
                    n_estimators=self.n_estimators, 
                    max_depth=self.max_depth,
                    random_state=42,
                    n_jobs=1 # Single thread to avoid overhead during Optuna multiprocessing
                )
                model.fit(train_X, train_y)
                
                # Predict (Probability of Class 1)
                preds = model.predict_proba(test_X)[:, 1]
                
                # Thresholding
                long_cond = preds > self.prob_thresh
                short_cond = preds < (1.0 - self.prob_thresh)
                
                block_signal = np.zeros(len(test_X), dtype=int)
                block_signal[long_cond] = 1
                block_signal[short_cond] = -1
                
                signal_array[test_start:test_end] = block_signal
                
            # 3. State Management (Convert to Entry Signals)
            signal_diff = np.diff(signal_array, prepend=0)
            entry_signals = np.zeros(len(df), dtype=int)
            entry_signals[(signal_array == 1) & (signal_diff > 0)] = 1
            entry_signals[(signal_array == -1) & (signal_diff < 0)] = -1
            
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
