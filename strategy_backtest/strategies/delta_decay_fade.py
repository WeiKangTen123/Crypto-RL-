import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import calc_decay_linear

class DeltaDecayFade(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Delta Decay Fade × Momentum (WorldQuant Alpha #39).
    Formula: (-1 * rank(delta(close, 7) * (1 - rank(decay_linear((volume / adv20), 9))))) * (1 + rank(sum(returns, 250)))
    
    This "HARD" factor fuses short-term mean reversion with a long-term macro trend filter.
    1. It tracks abnormal volume spikes (volume / adv).
    2. It applies a linear decay to these spikes to fade the "crowd" (heavy volume = lower multiplier).
    3. It multiplies this fade against the 7-period price delta, creating a short-term signal that 
       penalizes momentum driven by exhaustion volume.
    4. Finally, it amplifies the entire signal using a 250-period macro trend rank, ensuring it 
       only fires mean-reversion trades in the direction of the dominant macro regime.
    """
    
    SIGNAL_PARAMS = frozenset({'adv_p', 'decay_p', 'delta_p', 'macro_p', 'long_thresh', 'short_thresh'})
    
    OPTIMIZATION_RANGES = {
        'adv_p': [10, 20, 30, 50],
        'decay_p': [5, 9, 15, 30],
        'delta_p': [3, 7, 14, 21],
        'macro_p': [100, 250, 500, 1000],  # Macro trend lookback (4h bars)
        'long_thresh': [-0.5, -0.2, 0.0, 0.2, 0.5], # Signal is a multiplication of -rank and (1+rank)
        'short_thresh': [-1.5, -1.0, -0.8, -0.5],
        'sl_pct': [0.03, 0.05, 0.10, 0.15],
        'tp_pct': [0.05, 0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, adv_p=20, decay_p=9, delta_p=7, macro_p=250, long_thresh=0.0, short_thresh=-1.0, sl_pct=0.08, tp_pct=0.10, **kwargs):
        super().__init__(dfs, **kwargs)
        self.adv_p = int(adv_p)
        self.decay_p = int(decay_p)
        self.delta_p = int(delta_p)
        self.macro_p = int(macro_p)
        self.long_thresh = float(long_thresh)
        self.short_thresh = float(short_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        close_df = pd.DataFrame({sym: df['Close'] for sym, df in self.dfs.items()})
        vol_df = pd.DataFrame({sym: df['Volume'] for sym, df in self.dfs.items()})
        
        # adv20
        adv = vol_df.rolling(self.adv_p).mean()
        
        # volume / adv20
        vol_ratio = vol_df / (adv + 1e-8)
        
        # decay_linear((volume / adv20), 9)
        decay_vol = calc_decay_linear(vol_ratio, self.decay_p)
        
        # rank(decay_linear) - cross sectional
        rank_decay = decay_vol.rank(axis=1, pct=True)
        
        # fade = 1 - rank
        fade = 1.0 - rank_decay
        
        # delta(close, 7)
        delta_close = close_df.diff(self.delta_p)
        
        # delta * fade
        delta_fade = delta_close * fade
        
        # -1 * rank(delta * fade)
        part_d = -1.0 * delta_fade.rank(axis=1, pct=True)
        
        # sum(returns, 250)
        # return = close / close.shift(1) - 1
        returns = close_df.pct_change(1)
        sum_returns = returns.rolling(self.macro_p).sum()
        
        # 1 + rank(sum(returns, 250))
        part_e = 1.0 + sum_returns.rank(axis=1, pct=True)
        
        # Final Alpha
        raw_alpha = part_d * part_e
        
        for sym, df in self.dfs.items():
            alpha = raw_alpha[sym].loc[df.index]
            
            long_cond = alpha > self.long_thresh
            short_cond = alpha < self.short_thresh
            
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
