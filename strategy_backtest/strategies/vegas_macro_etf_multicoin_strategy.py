import numpy as np
import pandas as pd
import talib
from pathlib import Path
from typing import Optional, Tuple, Dict

from strategy_backtest.multi_base_strategy import MultiCoinBaseStrategy
from strategy_backtest.library import (
    calc_vegas_tunnel,
    calc_vegas_macro_tunnel,
    calc_vegas_distance_zscore,
    calc_zscore,
    calc_atr,
    calc_adx,
    calc_sma,
    calc_macro_regime_index,
    calc_etf_flow_proxy
)

class VegasMacroETFPortfolioStrategy(MultiCoinBaseStrategy):
    """
    Strategy 261 & 262: Macro Market Map & Spot Bitcoin ETF Enhanced Multi-Coin Vegas Portfolio.
    
    Synthesizes:
    1. Cross-Asset Macro Market Map (SPY, DXY, VIX, JPY):
       - Computes calc_macro_regime_index to gauge global risk-on appetite.
       - Macro Panic Veto closes open longs and halts entries during equity dumps, VIX spikes, or Yen carry unwinds.
    2. Spot Bitcoin ETF Institutional Flow Engine (IBIT, FBTC):
       - Computes calc_etf_flow_proxy to monitor institutional ETF accumulation vs distribution.
       - Outflow alert prevents altcoin trap breakouts during institutional selling waves.
    3. BTC Vegas Macro Anchor: Restricts altcoin entries when BTC is in a macro downtrend.
    4. Cross-Sectional Z-Score & Relative Alpha Ranking: Ranks liquid universe assets and selects Top-K leaders.
    5. Market Breadth Circuit Breaker: Freezes new entries when universe breadth drops below threshold.
    6. Two-Stage Ratchet Trade Management:
       - Initial SL at 2.0x ATR
       - Breakeven ratchet at 1.0x - 1.2x ATR
       - Chandelier trailing stop at 1.8x - 2.0x ATR from peak
       - Structural trend break exit when Close < Vegas Tunnel lower band (EMA 144)
    """

    SIGNAL_PARAMS = frozenset({
        'top_k', 'p_fast', 'p_slow', 'p_macro', 'z_thresh',
        'adx_thresh', 'breadth_thresh', 'macro_min_score', 'be_atr_mult', 'trail_atr_mult', 'sl_atr_mult'
    })

    OPTIMIZATION_RANGES = {
        'top_k': [2, 3, 4],
        'p_fast': (120, 160),
        'p_slow': (150, 190),
        'p_macro': (500, 700),
        'z_thresh': (0.3, 0.8),
        'adx_thresh': (16.0, 24.0),
        'breadth_thresh': (0.30, 0.45),
        'macro_min_score': (0.35, 0.55),
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
        z_thresh: float = 0.40,
        adx_thresh: float = 18.0,
        breadth_thresh: float = 0.35,
        macro_min_score: float = 0.40,
        be_atr_mult: float = 1.2,
        trail_atr_mult: float = 2.0,
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
        self.macro_min_score = float(macro_min_score)
        self.be_atr_mult = float(be_atr_mult)
        self.trail_atr_mult = float(trail_atr_mult)
        self.sl_atr_mult = float(sl_atr_mult)

        # State tracking per position
        self._pos_state: Dict[str, dict] = {}
        self._dataset_root = Path('/Users/weikangten/Desktop/Crypto-RL/dataset')

    def _load_macro_and_etf(self, common_idx: pd.DatetimeIndex) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        macro_dfs = {}
        for m in ['SPY', 'DXY', 'VIX', 'JPY', 'IBIT', 'FBTC']:
            p = self._dataset_root / m / '4h' / 'spot_ohlcv.parquet'
            if not p.exists():
                raise FileNotFoundError(f"Macro parquet missing at {p}")
            df = pd.read_parquet(p)
            t_col = 'open_time' if 'open_time' in df.columns else 'timestamp'
            df[t_col] = pd.to_datetime(df[t_col])
            df = df.sort_values(t_col).drop_duplicates(t_col).set_index(t_col)
            macro_dfs[m] = df.reindex(common_idx).ffill().bfill()

        macro_score, macro_veto = calc_macro_regime_index(
            macro_dfs['SPY'], macro_dfs['DXY'], macro_dfs['VIX'], macro_dfs['JPY']
        )
        etf_score, etf_outflow_alert = calc_etf_flow_proxy(
            macro_dfs['IBIT'], macro_dfs['FBTC']
        )

        return macro_score, macro_veto, etf_score, etf_outflow_alert

    def generate_signals(self) -> Dict[str, pd.DataFrame]:
        symbols = list(self.dfs.keys())
        first_sym = symbols[0]
        common_idx = self.dfs[first_sym].index
        for s in symbols[1:]:
            common_idx = common_idx.intersection(self.dfs[s].index)

        aligned_dfs = {s: self.dfs[s].loc[common_idx].copy() for s in symbols}

        # Identify BTC for macro anchor
        btc_sym = next((s for s in symbols if 'BTC' in s), symbols[0])
        btc_close = aligned_dfs[btc_sym]['Close']

        # Load Macro Market Map and Spot ETF flow signals
        macro_score, macro_veto, etf_score, etf_outflow_alert = self._load_macro_and_etf(common_idx)

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
            df['macro_score'] = macro_score
            df['macro_veto'] = macro_veto
            df['etf_outflow_alert'] = etf_outflow_alert

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

        # 4. Generate Entry Signals
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
            alpha_ok = df['rel_alpha'] > -0.05

            macro_pass = (~macro_veto) & (macro_score >= self.macro_min_score)
            etf_pass = ~etf_outflow_alert

            entry_cond = (
                vegas_break & macro_bull & mom_ok & vol_ok & breadth_ok &
                anchor_ok & top_k_ok & not_overextended & alpha_ok & macro_pass & etf_pass
            )
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

        # 1. Macro Panic Shock Exit: Immediate liquid de-risking
        if bool(row.get('macro_veto', False)):
            del self._pos_state[symbol]
            return 'EXIT', price

        # 2. Hard Stop Loss hit
        if low <= state['sl']:
            del self._pos_state[symbol]
            return 'SL', state['sl']

        # 3. Structural Vegas Tunnel breakdown exit
        vegas_bot = row.get('vegas_bot', row.get('vegas_top', entry_price * 0.95))
        if price < vegas_bot:
            del self._pos_state[symbol]
            return 'EXIT', price

        # 4. ETF Outflow or Macro Headwind: Tighten profit lock
        if bool(row.get('etf_outflow_alert', False)) and price > entry_price:
            pos_be = entry_price + (0.15 * atr_val)
            if pos_be > state['sl']:
                state['sl'] = pos_be
                state['be_active'] = True

        # 5. Breakeven Ratchet: if price reaches entry + (be_atr_mult * ATR)
        if not state['be_active'] and price >= entry_price + (self.be_atr_mult * atr_val):
            be_sl = entry_price + (0.15 * atr_val)
            if be_sl > state['sl']:
                state['sl'] = be_sl
                state['be_active'] = True

        # 6. Chandelier Trailing Stop: if price reaches entry + 2.5x ATR
        if price >= entry_price + (2.5 * atr_val):
            trail_sl = state['high_water'] - (self.trail_atr_mult * atr_val)
            if trail_sl > state['sl']:
                state['sl'] = trail_sl

        return 'HOLD', None
