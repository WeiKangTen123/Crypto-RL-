import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy
from strategy_backtest.library import calc_vwap, calc_atr, calc_rsi

class DVASStrategy(BaseStrategy):
    """
    Dynamic VWAP ATR Scalper (DVAS)
    Mean-reversion strategy that fades extreme price deviations from the VWAP.
    It triggers when price stretches too far from the volume-weighted mean,
    confirmed by RSI extremes and volume exhaustion spikes.
    """
    
    VALID_ACTIONS = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    SIGNAL_PARAMS = frozenset({
        'atr_dev_thresh', 'rsi_extreme', 'vol_spike_mult',
        'tp_multiplier', 'sl_multiplier'
    })

    # Custom optimization ranges for Optuna
    # sl_multiplier min=0.3: below this the SL is inside bid-ask spread and unfillable
    # vol_spike_mult min=1.0: below 1.0 is below-average volume, defeating exhaustion logic
    OPTIMIZATION_RANGES = {
        'atr_dev_thresh': (0.5, 4.0),
        'rsi_extreme': (5, 45),
        'vol_spike_mult': (1.0, 5.0),
        'tp_multiplier': (0.5, 5.0),
        'sl_multiplier': (0.3, 3.0),
    }

    def __init__(self, df: pd.DataFrame,
                 atr_dev_thresh: float = 0.9274,
                 rsi_extreme: float = 18.7729,
                 vol_spike_mult: float = 4.2345,
                 tp_multiplier: float = 1.6531,
                 sl_multiplier: float = 1.9795,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.atr_dev_thresh = float(atr_dev_thresh)
        self.rsi_extreme = float(rsi_extreme)
        self.vol_spike_mult = float(vol_spike_mult)
        self.tp_multiplier = float(tp_multiplier)
        self.sl_multiplier = float(sl_multiplier)
        
    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # Calculate Indicators
        df['vwap'] = calc_vwap(df)
        df['atr'] = calc_atr(df, 14)
        df['rsi'] = calc_rsi(df['Close'], 14)
        df['vol_ma'] = df['Volume'].rolling(20).mean()
        
        # Price deviation from VWAP
        dev_down = df['vwap'] - (self.atr_dev_thresh * df['atr'])
        dev_up = df['vwap'] + (self.atr_dev_thresh * df['atr'])
        
        # Long Conditions
        # 1. Price is stretched below VWAP
        # 2. RSI is oversold
        # 3. Volume is spiking (exhaustion)
        long_cond = (
            (df['Close'] < dev_down) &
            (df['rsi'] < self.rsi_extreme) &
            (df['Volume'] > self.vol_spike_mult * df['vol_ma'])
        )
        
        # Short Conditions
        # 1. Price is stretched above VWAP
        # 2. RSI is overbought
        # 3. Volume is spiking (exhaustion)
        short_cond = (
            (df['Close'] > dev_up) &
            (df['rsi'] > (100 - self.rsi_extreme)) &
            (df['Volume'] > self.vol_spike_mult * df['vol_ma'])
        )
        
        df['signal'] = 0
        df.loc[long_cond, 'signal'] = 1
        df.loc[short_cond, 'signal'] = -1
        
        self.df = df
        return self.df

    def manage_trade(self, row: pd.Series, position: float, entry_price: float, _wallet: float = 0):
        current_atr = row['atr']

        if position > 0:
            tp = entry_price + (self.tp_multiplier * current_atr)
            sl = entry_price - (self.sl_multiplier * current_atr)
            if row['Low']  <= sl: return 'SL', sl
            if row['High'] >= tp: return 'TP', tp

        elif position < 0:
            tp = entry_price - (self.tp_multiplier * current_atr)
            sl = entry_price + (self.sl_multiplier * current_atr)
            if row['High'] >= sl: return 'SL', sl
            if row['Low']  <= tp: return 'TP', tp

        return 'HOLD', None
