#!/usr/bin/env python3
"""
test_macro_etf_multicoin.py — Lead Architect / Crypto-RL
Full 5.5-Year backtest simulation comparing:
1. Baseline Multi-Coin Vegas Portfolio (10 & 12 coins)
2. Macro-Enhanced Vegas Portfolio (+SPY, DXY, VIX, JPY)
3. Full Macro + Spot ETF Flow Enhanced Vegas Portfolio (+IBIT, FBTC)
"""

import os
import sys
import numpy as np
import pandas as pd
import talib
from pathlib import Path

ROOT = Path('/Users/weikangten/Desktop/Crypto-RL')
sys.path.insert(0, str(ROOT))

from strategy_backtest.library import (
    calc_vegas_tunnel,
    calc_vegas_macro_tunnel,
    calc_zscore,
    calc_atr,
    calc_adx,
    calc_sma,
    calc_macro_regime_index,
    calc_etf_flow_proxy
)

UNIVERSE = [
    'BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'AVAX', 'ADA', 'BCH', 'XRP', 'LINK', 'DOT', 'LTC'
]

def load_data(coins):
    dfs = {}
    for c in coins:
        p = ROOT / 'dataset' / c / '4h' / 'spot_ohlcv.parquet'
        df = pd.read_parquet(p)
        df['open_time'] = pd.to_datetime(df['open_time'])
        df = df.sort_values('open_time').drop_duplicates('open_time').set_index('open_time')
        dfs[c] = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
        
    common = dfs['BTC'].index
    for c in coins:
        common = common.intersection(dfs[c].index)
        
    for c in coins:
        dfs[c] = dfs[c].loc[common].copy()
        
    # Load Macro and ETF data aligned to common
    macro_dfs = {}
    for m in ['SPY', 'DXY', 'VIX', 'JPY', 'IBIT', 'FBTC']:
        p = ROOT / 'dataset' / m / '4h' / 'spot_ohlcv.parquet'
        df = pd.read_parquet(p)
        df['open_time'] = pd.to_datetime(df['open_time'])
        df = df.sort_values('open_time').drop_duplicates('open_time').set_index('open_time')
        df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
        macro_dfs[m] = df.loc[common].copy()
        
    return dfs, macro_dfs, common

def simulate(
    coins,
    use_macro=True,
    use_etf=True,
    top_k=3,
    be_atr=1.2,
    trail_atr=2.0,
    sl_atr=2.0,
    leverage=1.5,
    use_inv_vol=True,
    macro_min_score=0.45
):
    dfs, macro_dfs, common_idx = load_data(coins)
    
    # 1. Compute Macro and ETF signals
    macro_score, macro_veto = calc_macro_regime_index(
        macro_dfs['SPY'], macro_dfs['DXY'], macro_dfs['VIX'], macro_dfs['JPY']
    )
    etf_score, etf_outflow_alert = calc_etf_flow_proxy(
        macro_dfs['IBIT'], macro_dfs['FBTC']
    )
    
    # 2. Compute Coin-Level Indicators
    btc_close = dfs['BTC']['Close']
    for c in coins:
        df = dfs[c]
        ema_f, ema_s, vegas_mid = calc_vegas_tunnel(df, 144, 169)
        ema_macro_f, _, _ = calc_vegas_macro_tunnel(df, 576, 676)
        ema_12 = talib.EMA(df['Close'], 12)
        
        atr = calc_atr(df, 14)
        adx = calc_adx(df, 14)
        vol_sma = calc_sma(df['Volume'], 20)
        z_price = calc_zscore(df['Close'], 20)
        
        dist = df['Close'] - vegas_mid
        z_dist = (dist - dist.rolling(20).mean()) / (dist.rolling(20).std() + 1e-8)
        rel_alpha = df['Close'].pct_change(60) - btc_close.pct_change(60)
        
        df['vegas_top'] = np.maximum(ema_f, ema_s)
        df['vegas_bot'] = np.minimum(ema_f, ema_s)
        df['ema_12'] = ema_12
        df['ema_macro'] = ema_macro_f
        df['atr'] = atr
        df['adx'] = adx
        df['z_price'] = z_price
        df['z_dist'] = z_dist
        df['rel_alpha'] = rel_alpha
        df['vol_confirm'] = df['Volume'] > (vol_sma * 0.85)
        df['is_bull'] = (df['Close'] > df['vegas_top']) & (df['Close'] > ema_macro_f)

    # 3. Market Breadth & BTC Anchor
    bull_matrix = pd.DataFrame({c: dfs[c]['is_bull'] for c in coins}, index=common_idx)
    market_breadth = bull_matrix.mean(axis=1)
    btc_bull = (dfs['BTC']['Close'] > dfs['BTC']['vegas_bot']) & (dfs['BTC']['Close'] > dfs['BTC']['ema_macro'])
    
    # 4. Cross-Sectional Ranking
    rank_score = pd.DataFrame({
        c: dfs[c]['z_price'] * (1.0 + dfs[c]['rel_alpha'].clip(-0.5, 0.5)) for c in coins
    }, index=common_idx)
    rank_matrix = rank_score.rank(axis=1, ascending=False)
    
    # 5. Signal Generation with Macro & ETF integration
    for c in coins:
        df = dfs[c]
        vegas_break = (df['Close'] > df['vegas_top']) & (df['ema_12'] > df['vegas_top'])
        macro_bull = df['Close'] > df['ema_macro']
        mom_ok = (df['z_price'] > 0.4) & (df['adx'] > 18.0)
        vol_ok = df['vol_confirm']
        breadth_ok = market_breadth >= 0.35
        anchor_ok = btc_bull if c != 'BTC' else pd.Series(True, index=common_idx)
        top_k_ok = rank_matrix[c] <= top_k
        not_overextended = df['z_dist'] < 2.8
        alpha_ok = df['rel_alpha'] > -0.05
        
        # Base entry condition
        entry_cond = vegas_break & macro_bull & mom_ok & vol_ok & breadth_ok & anchor_ok & top_k_ok & not_overextended & alpha_ok
        
        # Macro Gate
        if use_macro:
            macro_pass = (~macro_veto) & (macro_score >= macro_min_score)
            entry_cond = entry_cond & macro_pass
            
        # ETF Gate
        if use_etf:
            etf_pass = ~etf_outflow_alert
            entry_cond = entry_cond & etf_pass
            
        entry_trigger = entry_cond & (~entry_cond.shift(1, fill_value=False))
        df['signal'] = entry_trigger.astype(int)

    # 6. Portfolio Execution Simulation
    cash = 1000000.0
    initial_cash = 1000000.0
    positions = {}
    equity_curve = []
    trades = []
    fee_rate = 0.0005
    raw_events = []

    for i, t in enumerate(common_idx):
        if i < 600:
            continue
        current_prices = {c: dfs[c]['Close'].iloc[i] for c in coins}
        
        # Macro / ETF shock exit check
        is_macro_panic = bool(macro_veto.iloc[i]) if use_macro else False
        is_etf_dump = bool(etf_outflow_alert.iloc[i]) if use_etf else False
        
        # A. Check Exits
        to_close = []
        for c, pos in list(positions.items()):
            row = dfs[c].iloc[i]
            price = current_prices[c]
            sl = pos['sl']
            atr_v = row['atr']
            
            # SL hit
            if row['Low'] <= sl:
                exec_p = sl
                pnl = (exec_p - pos['entry_price']) * pos['qty']
                fee = exec_p * pos['qty'] * fee_rate
                cash += (pos['qty'] * pos['entry_price'] / leverage) + pnl - fee
                trades.append({'time': t, 'symbol': c, 'type': 'EXIT_LONG', 'price': exec_p, 'pnl': pnl, 'fee': fee, 'reason': 'SL'})
                raw_events.append({'time': t, 'symbol': c, 'target': 0.0, 'margin': pos['margin'], 'leverage': leverage})
                to_close.append(c)
                continue
                
            # Vegas Structural Breakdown Exit
            if row['Close'] < row['vegas_bot']:
                exec_p = row['Close']
                pnl = (exec_p - pos['entry_price']) * pos['qty']
                fee = exec_p * pos['qty'] * fee_rate
                cash += (pos['qty'] * pos['entry_price'] / leverage) + pnl - fee
                trades.append({'time': t, 'symbol': c, 'type': 'EXIT_LONG', 'price': exec_p, 'pnl': pnl, 'fee': fee, 'reason': 'VEGAS_EXIT'})
                raw_events.append({'time': t, 'symbol': c, 'target': 0.0, 'margin': pos['margin'], 'leverage': leverage})
                to_close.append(c)
                continue
                
            # Macro Panic / ETF Outflow Immediate Protection:
            # If Macro Veto or ETF dump fires, tighten SL to breakeven or Chandelier trail immediately
            if is_macro_panic or is_etf_dump:
                if price > pos['entry_price']:
                    pos['sl'] = max(pos['sl'], pos['entry_price'] + (0.10 * atr_v))
                else:
                    pos['sl'] = max(pos['sl'], price - (1.2 * atr_v))
                    
            # Breakeven Ratchet
            if be_atr > 0 and price >= pos['entry_price'] + (be_atr * atr_v):
                be_sl = pos['entry_price'] + (0.15 * atr_v)
                if be_sl > pos['sl']:
                    pos['sl'] = be_sl
                    
            # Chandelier Trailing Stop
            if trail_atr > 0 and price >= pos['entry_price'] + (2.5 * atr_v):
                t_sl = price - (trail_atr * atr_v)
                if t_sl > pos['sl']:
                    pos['sl'] = t_sl
                    
        for c in to_close:
            del positions[c]
            
        # B. Check Entries
        candidates = [c for c in coins if dfs[c]['signal'].iloc[i] == 1 and c not in positions]
        candidates.sort(key=lambda c: rank_score[c].iloc[i], reverse=True)
        
        for c in candidates:
            if len(positions) >= top_k:
                break
                
            unrealized = sum((current_prices[pc] - p['entry_price']) * p['qty'] for pc, p in positions.items())
            margin_locked = sum(p['qty'] * p['entry_price'] / leverage for p in positions.values())
            curr_equity = cash + margin_locked + unrealized
            
            # Dynamic Sizing scaled by macro confidence
            m_mult = float(macro_score.iloc[i]) if use_macro else 1.0
            m_mult = np.clip(m_mult, 0.60, 1.15)
            
            if use_inv_vol:
                atr_pct = dfs[c]['atr'].iloc[i] / current_prices[c]
                target_notional = curr_equity * (0.025 / (sl_atr * atr_pct)) * m_mult
                max_notional = (curr_equity * 0.90 / top_k) * leverage
                notional = min(target_notional, max_notional)
                target_margin = notional / leverage
            else:
                target_margin = (curr_equity * 0.90 / top_k) * m_mult
                notional = target_margin * leverage
                
            if cash < target_margin:
                target_margin = max(0, cash * 0.85)
                notional = target_margin * leverage
                
            if target_margin < 1000:
                continue
                
            entry_p = current_prices[c]
            qty = notional / entry_p
            fee = notional * fee_rate
            cash -= (target_margin + fee)
            
            positions[c] = {
                'qty': qty,
                'entry_price': entry_p,
                'sl': entry_p - (sl_atr * dfs[c]['atr'].iloc[i]),
                'margin': target_margin,
                'entry_bar': i
            }
            trades.append({'time': t, 'symbol': c, 'type': 'BUY', 'price': entry_p, 'pnl': 0.0, 'fee': fee, 'reason': 'ENTRY'})
            raw_events.append({'time': t, 'symbol': c, 'target': 1.0, 'margin': target_margin, 'leverage': leverage})
            
        unrealized = sum((current_prices[pc] - p['entry_price']) * p['qty'] for pc, p in positions.items())
        margin_locked = sum(p['qty'] * p['entry_price'] / leverage for p in positions.values())
        equity_curve.append(cash + margin_locked + unrealized)
        
    eq = pd.Series(equity_curve)
    ret_pct = (eq.iloc[-1] / initial_cash - 1.0) * 100.0
    peak = eq.cummax()
    dd = (eq - peak) / peak
    mdd = abs(dd.min()) * 100.0
    bar_rets = eq.pct_change().dropna()
    sharpe = (bar_rets.mean() / (bar_rets.std() + 1e-9)) * np.sqrt(2190) if bar_rets.std() > 0 else 0.0
    
    closed = [t for t in trades if t['type'] == 'EXIT_LONG']
    tdf = pd.DataFrame(closed)
    wr = (tdf['pnl'] > 0).mean() * 100.0 if not tdf.empty else 0.0
    gains = tdf[tdf['pnl'] > 0]['pnl'].sum() if not tdf.empty else 0.0
    losses = abs(tdf[tdf['pnl'] < 0]['pnl'].sum()) if not tdf.empty else 0.0
    pf = (gains / losses) if losses > 0 else 99.0
    
    return {
        'return_pct': ret_pct,
        'final_equity': eq.iloc[-1],
        'sharpe': sharpe,
        'mdd_pct': mdd,
        'win_rate': wr,
        'profit_factor': pf,
        'trades': len(closed),
        'signals': len(raw_events),
        'raw_events': raw_events
    }

if __name__ == '__main__':
    for name, m, e in [
        ('1. Baseline Vegas (No Macro/ETF)', False, False),
        ('2. + Cross-Asset Macro Market Map', True, False),
        ('3. + Full Macro + Spot ETF Flow Engine', True, True),
    ]:
        res = simulate(UNIVERSE, use_macro=m, use_etf=e)
        print(f"\n[{name}]")
        print(f"  Return:        +{res['return_pct']:.2f}% (${res['final_equity']:,.2f})")
        print(f"  Sharpe Ratio:  {res['sharpe']:.3f}")
        print(f"  Max Drawdown:  {res['mdd_pct']:.2f}%")
        print(f"  Win Rate:      {res['win_rate']:.2f}%")
        print(f"  Profit Factor: {res['profit_factor']:.2f}")
        print(f"  Closed Trades: {res['trades']}")
