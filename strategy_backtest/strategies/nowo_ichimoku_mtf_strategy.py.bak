import pandas as pd
import numpy as np
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy

class NowoIchimokuMTFStrategy(BaseStrategy):
    """
    Nowo Ichimoku MTF Strategy
    ==========================
    Category: Momentum / Trend Following
    Logic:
    1. Uses Ichimoku Cloud on a lower timeframe (e.g., 5m) for execution.
    2. Filters signals based on a higher timeframe (e.g., 1h) Ichimoku trend.
    3. Long: Close > Kumo, Tenkan > Kijun (on both timeframes).
    4. Short: Close < Kumo, Tenkan < Kijun (on both timeframes).
    """

    OPTIMIZATION_RANGES = {
        'tp_rr': (1.0, 25.0),  # Expanded for massive runners
        'signal_mode': ['CONSERVATIVE', 'BASE_ONLY', 'HTF_CLOUD_ONLY'],
        'exit_mode': ['CLOUD_CROSS', 'KIJUN_CROSS', 'TENKAN_CROSS'],
        'tenkan_period': (5, 30),
        'kijun_period': (10, 90),
        'senkou_b_period': (30, 200),
        'atr_period': (5, 77)
    }

    SIGNAL_PARAMS = frozenset({
        'tenkan_period',
        'kijun_period',
        'senkou_b_period',
        'displacement',
        'informative_tf',
        'sl_atr_mult',
        'tp_rr',
        'signal_mode',
        'exit_mode',
        'atr_period'
    })

    def __init__(
        self,
        df: pd.DataFrame,
        tenkan_period: int = 5,
        kijun_period: int = 22,
        senkou_b_period: int = 187,
        displacement: int = 26,
        informative_tf: str = '1h',
        sl_atr_mult: float = 2.6857,
        tp_rr: float = 20.664,
        signal_mode: str = 'CONSERVATIVE',
        exit_mode: str = 'CLOUD_CROSS',
        atr_period: int = 45,
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
        self.informative_tf = informative_tf
        self.sl_atr_mult = sl_atr_mult
        self.tp_rr = tp_rr
        self.signal_mode = signal_mode
        self.exit_mode = exit_mode
        self.atr_period = atr_period
        
        # State for trade management
        self._s = {
            1:  dict(sl_price=None, tp_price=None),
            -1: dict(sl_price=None, tp_price=None),
        }

    def _calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """Helper to calculate Ichimoku components."""
        res = pd.DataFrame(index=df.index)
        
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        res['tenkan'] = (df['High'].rolling(window=self.tenkan_period).max() + 
                         df['Low'].rolling(window=self.tenkan_period).min()) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        res['kijun'] = (df['High'].rolling(window=self.kijun_period).max() + 
                        df['Low'].rolling(window=self.kijun_period).min()) / 2
        
        # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2
        # Shifted forward by displacement (26)
        res['senkou_a'] = ((res['tenkan'] + res['kijun']) / 2).shift(self.displacement)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2
        # Shifted forward by displacement (26)
        res['senkou_b'] = ((df['High'].rolling(window=self.senkou_b_period).max() + 
                            df['Low'].rolling(window=self.senkou_b_period).min()) / 2).shift(self.displacement)
        
        # Kumo Cloud boundaries
        res['cloud_top'] = res[['senkou_a', 'senkou_b']].max(axis=1)
        res['cloud_bottom'] = res[['senkou_a', 'senkou_b']].min(axis=1)
        
        return res

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        for col in ['High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 1. Base Timeframe Ichimoku
        base_ichi = self._calculate_ichimoku(df)
        df['base_tenkan'] = base_ichi['tenkan']
        df['base_kijun'] = base_ichi['kijun']
        df['base_cloud_top'] = base_ichi['cloud_top']
        df['base_cloud_bottom'] = base_ichi['cloud_bottom']
        
        # 2. Informative Timeframe Ichimoku
        df_inf = df.resample(self.informative_tf).agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
        })
        inf_ichi = self._calculate_ichimoku(df_inf)
        
        # Align back to base dataframe
        df['inf_close'] = df_inf['Close'].reindex(df.index, method='ffill')
        df['inf_cloud_top'] = inf_ichi['cloud_top'].reindex(df.index, method='ffill')
        df['inf_cloud_bottom'] = inf_ichi['cloud_bottom'].reindex(df.index, method='ffill')
        df['inf_tenkan'] = inf_ichi['tenkan'].reindex(df.index, method='ffill')
        df['inf_kijun'] = inf_ichi['kijun'].reindex(df.index, method='ffill')
        
        
        # 3. ATR for SL/TP
        df.dropna(inplace=True) # Ensure no NaNs before TA-Lib calculations
        import talib
        df['atr'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=self.atr_period)
        
        # 4. Entry Conditions
        base_long = (df['Close'] > df['base_cloud_top']) & (df['base_tenkan'] > df['base_kijun'])
        base_short = (df['Close'] < df['base_cloud_bottom']) & (df['base_tenkan'] < df['base_kijun'])

        inf_long = (df['inf_close'] > df['inf_cloud_top']) & (df['inf_tenkan'] > df['inf_kijun'])
        inf_short = (df['inf_close'] < df['inf_cloud_bottom']) & (df['inf_tenkan'] < df['inf_kijun'])

        inf_cloud_long = (df['inf_close'] > df['inf_cloud_top'])
        inf_cloud_short = (df['inf_close'] < df['inf_cloud_bottom'])

        # ── Logic Switch Application ───────────────────────────────────────
        if self.signal_mode == 'CONSERVATIVE':
            # Requires Full Alignment (Base + HTF Trend)
            long_cond = base_long & inf_long
            short_cond = base_short & inf_short
        elif self.signal_mode == 'BASE_ONLY':
            # Aggressive: Ignores HTF entirely
            long_cond = base_long
            short_cond = base_short
        elif self.signal_mode == 'HTF_CLOUD_ONLY':
            # Medium: Requires HTF price to be above cloud, but ignores HTF Tenkan/Kijun cross
            long_cond = base_long & inf_cloud_long
            short_cond = base_short & inf_cloud_short
        else:
            long_cond = base_long & inf_long
            short_cond = base_short & inf_short
        
        signals = np.zeros(len(df), dtype=int)
        signals[long_cond] = 1
        signals[short_cond] = -1
        
        df['signal'] = signals
        self.df = df
        return df

    def manage_trade(
        self,
        row,
        position: float,
        entry_price: float,
        wallet: float = 0.0,
    ) -> Tuple[str, Optional[float]]:
        
        if position == 0:
            return 'HOLD', None
            
        side = int(np.sign(position))
        s = self._s[side]
        
        # Get ATR and Ichimoku values for the current row
        atr = row['atr']
        if np.isnan(atr): 
            atr = entry_price * 0.01 # Fallback
            
        # Initialize SL/TP on entry
        if entry_price != getattr(self, f'_last_entry_price_{side}', None):
            setattr(self, f'_last_entry_price_{side}', entry_price)
            s['sl_price'] = entry_price - side * (atr * self.sl_atr_mult)
            s['tp_price'] = entry_price + side * (atr * self.sl_atr_mult * self.tp_rr)

        # SL/TP Checks
        price_low = float(row['Low'])
        price_high = float(row['High'])
        price_close = float(row['Close'])
        
        if side == 1:
            if price_low  <= s['sl_price']: return 'SL', s['sl_price']
            if price_high >= s['tp_price']: return 'TP', s['tp_price']

            if self.exit_mode == 'CLOUD_CROSS':
                if price_close < row['base_cloud_bottom']: return 'EXIT', price_close
            elif self.exit_mode == 'KIJUN_CROSS':
                if price_close < row['base_kijun']: return 'EXIT', price_close
            elif self.exit_mode == 'TENKAN_CROSS':
                if price_close < row['base_tenkan']: return 'EXIT', price_close
        else:
            if price_high >= s['sl_price']: return 'SL', s['sl_price']
            if price_low  <= s['tp_price']: return 'TP', s['tp_price']

            if self.exit_mode == 'CLOUD_CROSS':
                if price_close > row['base_cloud_top']: return 'EXIT', price_close
            elif self.exit_mode == 'KIJUN_CROSS':
                if price_close > row['base_kijun']: return 'EXIT', price_close
            elif self.exit_mode == 'TENKAN_CROSS':
                if price_close > row['base_tenkan']: return 'EXIT', price_close

        return 'HOLD', None
