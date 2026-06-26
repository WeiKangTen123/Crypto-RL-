import pandas as pd
from strategy_backtest.base_strategy import BaseStrategy

class EMACrossoverStrategy(BaseStrategy):
    """
    A simple trend-following strategy based on EMA crossovers.
    """
    OPTIMIZATION_RANGES = {
        'fast_period':      (5,   50),
        'slow_period':      (20, 200),
        'volatility_filter':['ATR_GATED', 'NONE'],
        'atr_threshold':    (0.5,  3.0),
        'direction_mode':   ['BOTH', 'LONG_ONLY', 'SHORT_ONLY'],
    }

    SIGNAL_PARAMS = frozenset({
        'fast_period', 'slow_period', 'volatility_filter', 'atr_threshold', 'direction_mode'
    })

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.fast_period = kwargs.get('fast_period', 9)
        self.slow_period = kwargs.get('slow_period', 21)
        self.volatility_filter = kwargs.get('volatility_filter', 'NONE')
        self.atr_threshold = kwargs.get('atr_threshold', 1.5)
        self.direction_mode = kwargs.get('direction_mode', 'BOTH')

    def generate_signals(self) -> pd.DataFrame:
        """
        Generate entry signals based on EMA crossovers.
        """
        import talib
        df = self.df
        df['fast_ema'] = df['Close'].ewm(span=self.fast_period, adjust=False).mean()
        df['slow_ema'] = df['Close'].ewm(span=self.slow_period, adjust=False).mean()

        # Signal 1 for long, -1 for short
        df['raw_state'] = 0
        df.loc[df['fast_ema'] > df['slow_ema'], 'raw_state'] = 1
        df.loc[df['fast_ema'] < df['slow_ema'], 'raw_state'] = -1

        # Generate crossover/crossunder signals for entries
        df['crossover'] = df['raw_state'].diff()

        # Filter for actual entries
        df['signal'] = 0
        if self.direction_mode != 'SHORT_ONLY':
            df.loc[df['crossover'] == 2, 'signal'] = 1   # From -1 to 1
        if self.direction_mode != 'LONG_ONLY':
            df.loc[df['crossover'] == -2, 'signal'] = -1  # From 1 to -1

        # Volatility Gating
        if self.volatility_filter == 'ATR_GATED':
            df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
            df['atr_ma'] = df['atr'].rolling(window=100).mean()
            # Only trade if current ATR > threshold * average ATR (Volatility is high enough)
            vol_ok = df['atr'] > (df['atr_ma'] * self.atr_threshold)
            df.loc[~vol_ok, 'signal'] = 0

        return df

    def manage_trade(self, row, position: float, entry_price: float, wallet: float = 0):
        """
        Exit the trade when the EMAs cross in the opposite direction.
        """
        if position > 0:  # Long position
            if row['fast_ema'] < row['slow_ema']:
                return 'EXIT', None
        elif position < 0:  # Short position
            if row['fast_ema'] > row['slow_ema']:
                return 'EXIT', None
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        """Ensure fast_period is less than slow_period."""
        return params.get('fast_period', 9) < params.get('slow_period', 21)
