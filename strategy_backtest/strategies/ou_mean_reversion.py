import numpy as np
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_ou_mr_speed, calc_vwap_zscore

class OUMeanReversion(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Ornstein-Uhlenbeck Mean-Reversion
    Uses the OU mean-reversion speed (kappa) to filter trades.
    A high kappa (e.g., > 30) indicates that the asset is currently in a fast 
    mean-reverting regime, making mean-reversion trades safer.
    A low kappa indicates a trending regime where mean-reversion will likely fail.
    
    Entry: Price deviates from VWAP (z-score) AND kappa > min_kappa.
    """
    
    SIGNAL_PARAMS = frozenset({'ou_period', 'vwap_period', 'entry_z', 'min_kappa'})
    
    OPTIMIZATION_RANGES = {
        'ou_period': [10, 20, 60],
        'vwap_period': [10, 20, 40],
        'entry_z': [1.5, 2.0, 2.5],
        'min_kappa': [5, 10, 30, 50],
        'sl_pct': [0.03, 0.05, 0.08],
        'tp_pct': [0.03, 0.05, 0.10],
    }

    def __init__(self, dfs, ou_period=20, vwap_period=20, entry_z=2.0, min_kappa=30, sl_pct=0.05, tp_pct=0.05, **kwargs):
        super().__init__(dfs, **kwargs)
        self.ou_period = int(ou_period)
        self.vwap_period = int(vwap_period)
        self.entry_z = float(entry_z)
        self.min_kappa = float(min_kappa)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        for sym, df in self.dfs.items():
            kappa = calc_ou_mr_speed(df, period=self.ou_period)
            zscore, _ = calc_vwap_zscore(df, period=self.vwap_period)
            
            # High kappa = fast mean reversion
            mr_regime = kappa > self.min_kappa
            
            long_cond = (zscore < -self.entry_z) & mr_regime
            short_cond = (zscore > self.entry_z) & mr_regime
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond] = 1
            signal[short_cond] = -1
            
            # Transition into trade
            signal_diff = np.diff(signal, prepend=0)
            entry_signals = np.zeros(len(df), dtype=int)
            entry_signals[(signal == 1) & (signal_diff > 0)] = 1
            entry_signals[(signal == -1) & (signal_diff < 0)] = -1
            
            self.dfs[sym]['signal'] = entry_signals
            
        return self.dfs

    def manage_trade(self, symbol: str, bar, qty: float, entry_price: float, entry_balance: float):
        """
        Fixed RR exit management. Since it's mean reversion, we might take quicker profits.
        """
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
