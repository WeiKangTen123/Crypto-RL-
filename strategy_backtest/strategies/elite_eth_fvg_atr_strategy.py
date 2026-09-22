"""
Elite ETH FVG + ATR Strategy
==============================================================================
Ported from the original OKX-era Elite Combined Portfolio
(paper_trade/combined_portfolio_paper.py, process_eth). Detects Fair Value Gaps
(3-bar imbalance) confirmed by an ATR-based momentum filter (price beyond MA +/-
ATR), with ATR-multiple TP/SL management.

This is the ETH leg of the original ETH+DOT+SOL Elite portfolio that earned
Signal Strive Run B Grade C (score 67.2/100, Sharpe 1.68, +11.9% return, 25.7%
MDD) -- run_id sr_cc302e2431. Ported here as a BaseStrategy class so the
Binance execution engine can run it directly (previously the live "Elite"
portfolio was mistakenly wired to unrelated single-coin strategies #126/#23/#13,
none of which ever produced that graded result).
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from strategy_backtest.base_strategy import BaseStrategy


class EliteEthFvgAtrStrategy(BaseStrategy):
    OPTIMIZATION_RANGES = {}

    def __init__(self, df: pd.DataFrame, **kwargs):
        super().__init__(df, **kwargs)
        self.atr_period       = kwargs.get('atr_period', 24)
        self.fvg_period        = kwargs.get('fvg_period', 43)
        self.tp_atr_mult       = kwargs.get('tp_atr_mult', 4.6029)
        self.sl_atr_mult       = kwargs.get('sl_atr_mult', 1.9697)
        self.fvg_min_strength  = kwargs.get('fvg_min_strength', 0.001)

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        H, L, C = df['High'], df['Low'], df['Close']

        prev_close = C.shift(1)
        tr = pd.concat([H - L, (H - prev_close).abs(), (L - prev_close).abs()], axis=1).max(axis=1)
        df['atr'] = tr.rolling(self.atr_period).mean()
        df['ma_fvg'] = C.rolling(self.fvg_period).mean()

        # FVG 3-bar pattern: b0 = i-2, b1 = i-1 (the displacement bar), b2 = i (current).
        # The imbalance is measured between bar 0 and bar 2 -- bar 1 is the candle that
        # gaps price across, so it is deliberately NOT part of the comparison.
        # This previously compared bar 0's high against bar 1's low (h0 < l1), i.e. two
        # ADJACENT bars. On continuous 4h crypto data adjacent bars essentially always
        # overlap, so the condition was never true even once across 11,857 ETH bars: #900
        # emitted ZERO signals for its whole history and the ELITE portfolio was running
        # with no ETH leg at all. Comparing bar 0 to bar 2 (the actual FVG definition, and
        # what the strategy's own docstring describes) yields 1,123 signals on that range.
        h0, l0 = H.shift(2), L.shift(2)
        c0 = C.shift(2)
        bull_gap = h0 < L
        bull_strength = (L - h0) / c0.replace(0, np.nan)
        bear_gap = l0 > H
        bear_strength = (l0 - H) / c0.replace(0, np.nan)

        df['signal'] = 0
        long_ok = bull_gap & (df['atr'] > 0) & (bull_strength > self.fvg_min_strength) & (C > df['ma_fvg'] + df['atr'])
        short_ok = bear_gap & (df['atr'] > 0) & (bear_strength > self.fvg_min_strength) & (C < df['ma_fvg'] - df['atr'])
        df.loc[long_ok.fillna(False), 'signal'] = 1
        df.loc[short_ok.fillna(False), 'signal'] = -1

        self.df = df
        return df

    def manage_trade(self, row, position: float, entry_price: float,
                     wallet: float = 0) -> Tuple[str, Optional[float]]:
        atr = row.get('atr', np.nan)
        if pd.isna(atr) or atr <= 0:
            return 'HOLD', None
        if position > 0:
            tp_px = entry_price + self.tp_atr_mult * atr
            sl_px = entry_price - self.sl_atr_mult * atr
            sl_first = float(row['Close']) < float(row['Open'])
            if sl_first:
                if row['Low'] <= sl_px: return 'SL', sl_px
                if row['High'] >= tp_px: return 'TP', tp_px
            else:
                if row['High'] >= tp_px: return 'TP', tp_px
                if row['Low'] <= sl_px: return 'SL', sl_px
        elif position < 0:
            tp_px = entry_price - self.tp_atr_mult * atr
            sl_px = entry_price + self.sl_atr_mult * atr
            sl_first = float(row['Close']) > float(row['Open'])
            if sl_first:
                if row['High'] >= sl_px: return 'SL', sl_px
                if row['Low'] <= tp_px: return 'TP', tp_px
            else:
                if row['Low'] <= tp_px: return 'TP', tp_px
                if row['High'] >= sl_px: return 'SL', sl_px
        return 'HOLD', None

    @classmethod
    def validate_params(cls, params: dict) -> bool:
        return True
