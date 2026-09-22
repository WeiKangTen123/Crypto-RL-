import numpy as np
import pandas as pd
import talib
from typing import Optional, Tuple, Dict

from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import (
    calc_vegas_tunnel,
    calc_vegas_macro_tunnel,
    calc_vegas_distance_zscore,
    calc_zscore,
    calc_atr,
    calc_adx,
    calc_sma
)

class VegasMultiCoinPortfolioStrategy(MultiCoinBaseStrategy):
    """
    MULTI-COIN PORTFOLIO strategy: Vegas Tunnel + Z-Score Statistical Momentum & Risk Parity.
    
    Scales dynamically across 10 to 30 coins:
    1. BTC Vegas Macro Anchor: Restricts altcoin entries when BTC is in a macro downtrend.
    2. Cross-Sectional Z-Score Ranking: Ranks all eligible coins and selects Top-K momentum leaders.
    3. Market Breadth Circuit Breaker: Freezes new entries when breadth drops below threshold.
    4. Two-Stage Ratchet Trade Management:
       - Initial SL at 2.0x ATR
       - Breakeven ratchet at 1.0x ATR (locks SL at Entry + 0.15x ATR)
       - Chandelier trailing stop at 1.8x ATR from peak
       - Structural trend break exit when Close < Vegas Tunnel lower band (EMA 144)
    """

    SIGNAL_PARAMS = frozenset({
        'top_k', 'p_fast', 'p_slow', 'p_macro', 'z_thresh',
        'adx_thresh', 'breadth_thresh', 'be_atr_mult', 'trail_atr_mult', 'sl_atr_mult'
    })

    OPTIMIZATION_RANGES = {
        'top_k': [2, 3, 4, 5],
        'p_fast': (120, 160),
        'p_slow': (150, 190),
        'p_macro': (500, 700),
        'z_thresh': (0.3, 1.0),
        'adx_thresh': (16.0, 26.0),
        'breadth_thresh': (0.30, 0.50),
        'be_atr_mult': (0.8, 1.5),
        'trail_atr_mult': (1.5, 2.5),
        'sl_atr_mult': (1.5, 2.5)
    }

    def __init__(
        self,
        dfs: Dict[str, pd.DataFrame],
        top_k: int = 3,
        p_fast: int = 144,
        p_slow: int = 169,
        p_macro: int = 576,
        z_thresh: float = 0.45,
        adx_thresh: float = 18.0,
        breadth_thresh: float = 0.40,
        be_atr_mult: float = 1.0,
        trail_atr_mult: float = 1.8,
        sl_atr_mult: float = 2.0,
        **kwargs
    ):
        super().__init__(dfs, **kwargs)
        self.top_k = int(top_k)
        self.p_fast = int(p_fast)
        self.p_slow = int(p_slow)
        self.p_macro = int(p_macro)
        self.z_thresh = float(z_thresh)
        self.adx_thresh = float(adx_thresh)
        self.breadth_thresh = float(breadth_thresh)
        self.be_atr_mult = float(be_atr_mult)
        self.trail_atr_mult = float(trail_atr_mult)
        self.sl_atr_mult = float(sl_atr_mult)

        # State tracking per position
        self._pos_state: Dict[str, dict] = {}

    def generate_signals(self) -> Dict[str, pd.DataFrame]:
        # Intersect timestamps to align matrix calculations
        symbols = list(self.dfs.keys())
        first_sym = symbols[0]
        common_idx = self.dfs[first_sym].index
        for s in symbols[1:]:
            common_idx = common_idx.intersection(self.dfs[s].index)

        aligned_dfs = {s: self.dfs[s].loc[common_idx].copy() for s in symbols}

        # Identify BTC for macro anchor
        btc_sym = None
        for s in symbols:
            if 'BTC' in s:
                btc_sym = s
                break
        if btc_sym is None:
            btc_sym = symbols[0]

        btc_close = aligned_dfs[btc_sym]['Close']

        # 1. Compute indicators per coin via pure library functions
        for s in symbols:
            df = aligned_dfs[s]
            ema_fast, ema_slow, vegas_mid = calc_vegas_tunnel(df, self.p_fast, self.p_slow)
            ema_macro_f, _, _ = calc_vegas_macro_tunnel(df, self.p_macro, self.p_macro + 100)
            ema_12 = talib.EMA(df['Close'], 12)

            vegas_top = np.maximum(ema_fast, ema_slow)
            vegas_bot = np.minimum(ema_fast, ema_slow)

            atr = calc_atr(df, 14)
            adx = calc_adx(df, 14)
            vol_sma = calc_sma(df['Volume'], 20)
            z_price = calc_zscore(df['Close'], 20)

            dist = df['Close'] - vegas_mid
            z_dist = (dist - dist.rolling(20).mean()) / (dist.rolling(20).std() + 1e-8)
            rel_alpha = df['Close'].pct_change(60) - btc_close.pct_change(60)

            df['vegas_top'] = vegas_top
            df['vegas_bot'] = vegas_bot
            df['ema_macro'] = ema_macro_f
            df['ema_12'] = ema_12
            df['atr'] = atr
            df['adx'] = adx
            df['z_price'] = z_price
            df['z_dist'] = z_dist
            df['rel_alpha'] = rel_alpha
            df['vol_confirm'] = df['Volume'] > (vol_sma * 0.85)
            df['is_bull'] = (df['Close'] > vegas_top) & (df['Close'] > ema_macro_f)

        # 2. Market Breadth & BTC Anchor
        bull_matrix = pd.DataFrame({s: aligned_dfs[s]['is_bull'] for s in symbols}, index=common_idx)
        market_breadth = bull_matrix.mean(axis=1)

        btc_df = aligned_dfs[btc_sym]
        btc_bull = (btc_df['Close'] > btc_df['vegas_bot']) & (btc_df['Close'] > btc_df['ema_macro'])

        # 3. Cross-Sectional Ranking Matrix (Z-Score * (1 + Relative Alpha))
        rank_score = pd.DataFrame({
            s: aligned_dfs[s]['z_price'] * (1.0 + aligned_dfs[s]['rel_alpha'].clip(-0.5, 0.5)) for s in symbols
        }, index=common_idx)
        rank_matrix = rank_score.rank(axis=1, ascending=False)

        # 4. Generate Signals
        for s in symbols:
            df = aligned_dfs[s]
            vegas_break = (df['Close'] > df['vegas_top']) & (df['ema_12'] > df['vegas_top'])
            macro_bull = df['Close'] > df['ema_macro']
            mom_ok = (df['z_price'] > self.z_thresh) & (df['adx'] > self.adx_thresh)
            vol_ok = df['vol_confirm']
            breadth_ok = market_breadth >= self.breadth_thresh
            anchor_ok = btc_bull if s != btc_sym else pd.Series(True, index=common_idx)
            top_k_ok = rank_matrix[s] <= self.top_k
            not_overextended = df['z_dist'] < 2.8

            entry_cond = vegas_break & macro_bull & mom_ok & vol_ok & breadth_ok & anchor_ok & top_k_ok & not_overextended
            trigger = entry_cond & (~entry_cond.shift(1, fill_value=False))

            signal = np.zeros(len(df), dtype=int)
            signal[trigger.fillna(False)] = 1
            df['signal'] = signal

            self.dfs[s] = df

        return self.dfs

    def manage_trade(
        self,
        symbol: str,
        row: pd.Series,
        position: float,
        entry_price: float,
        wallet: float = 0,
    ) -> Tuple[str, Optional[float]]:
        if position == 0:
            if symbol in self._pos_state:
                del self._pos_state[symbol]
            return 'HOLD', None

        # Re-initialize state when entry price changes
        if symbol not in self._pos_state or self._pos_state[symbol]['entry_p'] != entry_price:
            atr_val = row.get('atr', entry_price * 0.02)
            init_sl = entry_price - (self.sl_atr_mult * atr_val)
            self._pos_state[symbol] = {
                'entry_p': entry_price,
                'sl': init_sl,
                'high_water': entry_price,
                'be_active': False
            }

        state = self._pos_state[symbol]
        price = row['Close']
        high = row['High']
        low = row['Low']
        atr_val = row.get('atr', entry_price * 0.02)

        # Update high water mark
        if high > state['high_water']:
            state['high_water'] = high

        # 1. Hard Stop Loss hit
        if low <= state['sl']:
            del self._pos_state[symbol]
            return 'SL', state['sl']

        # 2. Structural Vegas Tunnel breakdown exit
        vegas_bot = row.get('vegas_bot', row.get('vegas_top', entry_price * 0.95))
        if price < vegas_bot:
            del self._pos_state[symbol]
            return 'EXIT', price

        # 3. Breakeven Ratchet: if price reaches entry + (be_atr_mult * ATR)
        if not state['be_active'] and price >= entry_price + (self.be_atr_mult * atr_val):
            be_sl = entry_price + (0.15 * atr_val)
            if be_sl > state['sl']:
                state['sl'] = be_sl
                state['be_active'] = True

        # 4. Chandelier Trailing Stop: if price reaches entry + 2.2x ATR
        if price >= entry_price + (2.2 * atr_val):
            trail_sl = state['high_water'] - (self.trail_atr_mult * atr_val)
            if trail_sl > state['sl']:
                state['sl'] = trail_sl

        return 'HOLD', None
