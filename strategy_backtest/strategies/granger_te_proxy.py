import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class GrangerTEProxy(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Transfer Entropy (Granger Causality Proxy).
    
    This strategy implements a mathematical proxy for Causal Information Flow 
    (Transfer Entropy) from Bitcoin (the macro driver) to individual Altcoins.
    
    TE Proxy = CrossCorr(Altcoin_t, BTC_t-1) - AutoCorr(Altcoin_t, Altcoin_t-1)
    
    - If TE Proxy is highly POSITIVE: The Altcoin is heavily driven by BTC's past 
      moves rather than its own (it is a 'Beta Slave'). We trade it in the direction 
      of the BTC trend.
    - If TE Proxy is highly NEGATIVE: The Altcoin is decoupled from BTC and heavily 
      driven by its own internal dynamics (Idiosyncratic Alpha). We trade it in the 
      direction of its own trend.
    """
    
    SIGNAL_PARAMS = frozenset({'window', 'te_thresh', 'trend_window'})
    
    OPTIMIZATION_RANGES = {
        'window': [50, 100, 200, 300],
        'te_thresh': [0.1, 0.2, 0.3, 0.4],
        'trend_window': [10, 20, 50, 100],
        'sl_pct': [0.05, 0.08, 0.12, 0.15],
        'tp_pct': [0.10, 0.20, 0.30, 0.40],
    }

    def __init__(self, dfs, window=100, te_thresh=0.2, trend_window=20, sl_pct=0.08, tp_pct=0.20, **kwargs):
        super().__init__(dfs, **kwargs)
        self.window = int(window)
        self.te_thresh = float(te_thresh)
        self.trend_window = int(trend_window)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        # Require BTC for causal baseline
        if 'BTC' not in self.dfs:
            return self.dfs
            
        btc_df = self.dfs['BTC']
        btc_ret = btc_df['Close'].pct_change(1).fillna(0)
        btc_ret_lag = btc_ret.shift(1, fill_value=0)
        btc_trend = btc_df['Close'].pct_change(self.trend_window).fillna(0)
        
        for sym, df in self.dfs.items():
            if sym == 'BTC':
                # BTC cannot Granger-cause itself in this framework.
                self.dfs[sym]['signal'] = np.zeros(len(df), dtype=int)
                continue
                
            coin_ret = df['Close'].pct_change(1).fillna(0)
            coin_ret_lag = coin_ret.shift(1, fill_value=0)
            coin_trend = df['Close'].pct_change(self.trend_window).fillna(0)
            
            # Align lengths in case of missing data (e.g., MATIC is shorter)
            aligned_btc_ret_lag = btc_ret_lag.loc[df.index]
            aligned_btc_trend = btc_trend.loc[df.index]
            
            # 1. Autocorrelation
            auto_corr = coin_ret.rolling(self.window).corr(coin_ret_lag).fillna(0)
            
            # 2. Cross-correlation (BTC driving Coin)
            cross_corr = coin_ret.rolling(self.window).corr(aligned_btc_ret_lag).fillna(0)
            
            # 3. TE Proxy
            te_proxy = cross_corr - auto_corr
            
            # 4. Regime Trading Logic
            slave_long = (te_proxy > self.te_thresh) & (aligned_btc_trend > 0)
            slave_short = (te_proxy > self.te_thresh) & (aligned_btc_trend < 0)
            
            alpha_long = (te_proxy < -self.te_thresh) & (coin_trend > 0)
            alpha_short = (te_proxy < -self.te_thresh) & (coin_trend < 0)
            
            long_cond = slave_long | alpha_long
            short_cond = slave_short | alpha_short
            
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
