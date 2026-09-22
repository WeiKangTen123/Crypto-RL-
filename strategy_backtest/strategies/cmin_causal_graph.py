import numpy as np
import pandas as pd
from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy

class CminCausalGraph(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: CMIN Causal Graph (Lead-Lag Network).
    
    This is an advanced Graph Theory strategy. It dynamically calculates the 
    causal information flow (lagged cross-correlation) between all coins in 
    the portfolio to build a directed causal graph.
    
    For each coin:
    - In-Degree: How much its current price is predicted by the past price of others.
    - Out-Degree: How much its past price predicts the current price of others.
    - Net Influence = Out-Degree - In-Degree
    
    The coin with the highest Net Influence is the 'Market Leader'.
    The coins with the lowest Net Influence are the 'Followers'.
    
    Alpha Trigger: 
    When the Market Leader begins to surge (momentum > 0), we execute a BUY 
    on the Follower coins, because causal mechanics dictate they will inevitably 
    be dragged up.
    """
    
    SIGNAL_PARAMS = frozenset({'window', 'leader_trend_p', 'follower_thresh'})
    
    OPTIMIZATION_RANGES = {
        'window': [20, 50, 100, 200],
        'leader_trend_p': [5, 10, 20, 50],
        'follower_thresh': [0.1, 0.2, 0.3], # e.g. trade the bottom 20% of net influence
        'sl_pct': [0.05, 0.08, 0.10, 0.15],
        'tp_pct': [0.10, 0.20, 0.30],
    }

    def __init__(self, dfs, window=50, leader_trend_p=10, follower_thresh=0.2, sl_pct=0.08, tp_pct=0.15, **kwargs):
        super().__init__(dfs, **kwargs)
        self.window = int(window)
        self.leader_trend_p = int(leader_trend_p)
        self.follower_thresh = float(follower_thresh)
        self.sl_pct = float(sl_pct)
        self.tp_pct = float(tp_pct)
        
    def generate_signals(self) -> dict:
        # Build master dataframe of returns
        ret_dict = {}
        for sym, df in self.dfs.items():
            ret_dict[sym] = df['Close'].pct_change(1).fillna(0)
            
        ret_df = pd.DataFrame(ret_dict)
        ret_df_lag = ret_df.shift(1, fill_value=0)
        
        # Calculate Rolling Out-Degree and In-Degree
        # To make this fast in pandas, we approximate Net Influence:
        # Out-Degree of i = sum of corr(j_t, i_t-1) for all j
        # In-Degree of i = sum of corr(i_t, j_t-1) for all j
        
        coins = list(ret_df.columns)
        n = len(coins)
        
        net_influence = pd.DataFrame(index=ret_df.index, columns=coins)
        net_influence.values[:] = 0.0
        
        # We need to loop over time to build the dynamic graph.
        # But rolling pairwise correlation across N coins is O(N^2) per bar.
        # Since N=10, it's 100 corr calcs per bar.
        # Let's vectorize it using rolling sums.
        
        for i in coins:
            out_deg = pd.Series(0.0, index=ret_df.index)
            in_deg = pd.Series(0.0, index=ret_df.index)
            
            for j in coins:
                if i == j: continue
                
                # Out-degree for i: corr(j_t, i_t-1)
                corr_out = ret_df[j].rolling(self.window).corr(ret_df_lag[i]).fillna(0)
                out_deg += corr_out
                
                # In-degree for i: corr(i_t, j_t-1)
                corr_in = ret_df[i].rolling(self.window).corr(ret_df_lag[j]).fillna(0)
                in_deg += corr_in
                
            net_influence[i] = out_deg - in_deg
            
        # The Leader is the coin with the max net_influence at each bar
        leader_idx = net_influence.idxmax(axis=1)
        
        # We need the momentum of the leader
        mom_df = ret_df.rolling(self.leader_trend_p).sum() # approx momentum
        
        # We also need the threshold for followers (bottom percentile)
        # We can just rank the net_influence across axis=1
        influence_ranks = net_influence.rank(axis=1, pct=True)
        
        for sym, df in self.dfs.items():
            # Align everything to the coin's specific dataframe length (e.g. MATIC)
            aligned_leader_idx = leader_idx.loc[df.index]
            aligned_mom_df = mom_df.loc[df.index]
            aligned_influence_rank = influence_ranks.loc[df.index, sym]
            
            # Get the leader's momentum at each bar
            # We use numpy indexing to extract it efficiently
            # Need to map leader symbol to column index in mom_df
            sym_to_col = {c: idx for idx, c in enumerate(mom_df.columns)}
            col_indices = aligned_leader_idx.map(sym_to_col).fillna(0).astype(int)
            
            # Extract leader momentum
            # aligned_mom_df.values[row_idx, col_indices]
            row_idx = np.arange(len(aligned_mom_df))
            leader_momentum = aligned_mom_df.values[row_idx, col_indices.values]
            
            # Condition 1: Coin is a follower
            is_follower = aligned_influence_rank <= self.follower_thresh
            
            # Condition 2: Leader is surging
            long_cond = is_follower & (leader_momentum > 0.05) # Leader is up 5%
            short_cond = is_follower & (leader_momentum < -0.05) # Leader is down 5%
            
            signal = np.zeros(len(df), dtype=int)
            signal[long_cond.values] = 1
            signal[short_cond.values] = -1
            
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
