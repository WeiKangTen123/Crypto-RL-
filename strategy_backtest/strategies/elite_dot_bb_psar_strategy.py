"""
Elite DOT Bollinger Breakout + RSI Filter + Parabolic SAR Strategy
==============================================================================
Ported from the original OKX-era Elite Combined Portfolio
(paper_trade/combined_portfolio_paper.py, process_dot / DotState). Entry: price
breaks outside Bollinger Bands, confirmed by RSI not yet at the extreme zone
(breakout continuation, not mean-reversion). Exit: Parabolic SAR trailing stop
(SAR flip against the position) -- SAR is recomputed every bar, matching the
original stateful update() loop.

This is the DOT leg of the original ETH+DOT+SOL Elite portfolio that earned
Signal Strive Run B Grade C (score 67.2/100, Sharpe 1.68, +11.9% return, 25.7%
MDD) -- run_id sr_cc302e2431.
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy


class EliteDotBbPsarStrategy(BaseStrategy):
    OPTIMIZATION_RANGES = {}

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.bb_period       = kwargs.get('bb_period', 20)
        self.bb_std          = kwargs.get('bb_std', 2.0)
        self.rsi_period      = kwargs.get('rsi_period', 14)
        self.rsi_oversold    = kwargs.get('rsi_oversold', 30)
        self.rsi_overbought  = kwargs.get('rsi_overbought', 70)
        self.psar_af_step    = kwargs.get('psar_af', 0.0198)
        self.psar_af_max     = kwargs.get('psar_max', 0.3941)

    def _compute_psar(self, df: pd.DataFrame) -> pd.Series:
        """Iterative Parabolic SAR -- bar-for-bar replica of DotState.update()."""
        n = len(df)
        psar = np.full(n, np.nan)
        if n == 0:
            return pd.Series(psar, index=df.index)
        H = df['High'].values
        L = df['Low'].values
        sar = L[0]; af = self.psar_af_step; hp = H[0]; lp = L[0]; trend = 1
        psar[0] = sar
        for i in range(1, n):
            high, low = H[i], L[i]
            if trend == 1:
                if high > hp:
                    hp = high
                    af = min(af + self.psar_af_step, self.psar_af_max)
                sar = sar + af * (hp - sar)
                sar = min(sar, low)
                if low <= sar:
                    trend = -1; sar = hp; lp = low; af = self.psar_af_step
            else:
                if low < lp:
                    lp = low
                    af = min(af + self.psar_af_step, self.psar_af_max)
                sar = sar - af * (sar - lp)
                sar = max(sar, high)
                if high >= sar:
                    trend = 1; sar = lp; hp = high; af = self.psar_af_step
            psar[i] = sar
        return pd.Series(psar, index=df.index)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        C = df['Close']

        ma = C.rolling(self.bb_period).mean()
        std = C.rolling(self.bb_period).std(ddof=0)
        bb_upper = ma + self.bb_std * std
        bb_lower = ma - self.bb_std * std

        delta = C.diff()
        gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
        loss = (-delta.clip(upper=0)).rolling(self.rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).fillna(50.0)

        df['psar'] = self._compute_psar(df)

        df['signal'] = 0
        long_ok = (C > bb_upper) & (rsi < self.rsi_overbought)
        short_ok = (C < bb_lower) & (rsi > self.rsi_oversold)
        df.loc[long_ok.fillna(False), 'signal'] = 1
        df.loc[short_ok.fillna(False), 'signal'] = -1

        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float,
                     wallet: float = 0) -> Tuple[str, Optional[float]]:
        sar = row.get('psar', np.nan)
        if pd.isna(sar):
            return 'HOLD', None
        close = float(row['Close'])
        if position > 0 and close <= sar:
            return 'EXIT', sar
        if position < 0 and close >= sar:
            return 'EXIT', sar
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        return True
