#!/usr/bin/env python3
"""
submit_vegas_multicoin_portfolio.py — Multi-Coin Vegas Z-Score Portfolio Strategy
Evaluates and submits cross-margin multi-asset portfolios across 10 to 30 coins
to the Signal Strive / Signal Replay API.

Incorporates:
- Pure mathematical functions from strategy_backtest/library.py
- BTC Macro Vegas Anchor (Macro Shield)
- Cross-Sectional Z-Score & Relative Alpha Ranking
- Market Breadth Circuit Breaker
- Dynamic Risk Parity & Inverse-Volatility Sizing (MDD Minimizer)
- Two-Stage Ratchet Exit (Breakeven + Chandelier Trailing Stop)
"""

import sys
import os
import json
import time
import requests
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import talib

ROOT = Path('/Users/weikangten/Desktop/Crypto-RL')
sys.path.insert(0, str(ROOT))

from strategy_backtest.metrics import compute_metrics, _extract_numeric
from strategy_backtest.library import (
    calc_vegas_tunnel,
    calc_vegas_macro_tunnel,
    calc_zscore,
    calc_atr,
    calc_adx,
    calc_sma
)

SIGNAL_REPLAY_DIR = ROOT / 'Signal_Replay'
API_KEY_FILE = ROOT / 'API & others' / 'signal_replay_api.txt'
RUNS_FILE = SIGNAL_REPLAY_DIR / 'runs.json'
DATASET_ROOT = ROOT / 'dataset'

# Complete 30-Coin Universe
UNIVERSE_30 = [
    'BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'AVAX', 'ADA', 'BCH', 'XRP', 'LINK',
    'DOT', 'AAVE', 'LTC', 'ATOM', 'XLM', 'UNI', 'ETC', 'VET', 'COMP', 'MKR',
    'BAT', 'ZRX', 'NEO', 'QTUM', 'ONT', 'KNC', 'ONE', 'BAND', 'STORJ', 'EGLD'
]

def _load_api_key() -> str:
    raw = API_KEY_FILE.read_text().strip()
    return raw.split('=', 1)[-1].strip()

def load_coin_data(coin: str, tf: str = '4h') -> pd.DataFrame:
    p = DATASET_ROOT / coin / tf / 'spot_ohlcv.parquet'
    if not p.exists():
        raise FileNotFoundError(f"Parquet missing for {coin} at {p}")
    df = pd.read_parquet(p)
    df['open_time'] = pd.to_datetime(df['open_time'])
    df = df.sort_values('open_time').drop_duplicates('open_time').set_index('open_time')
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

def run_multicoin_portfolio(
    coins=None,
    tf='4h',
    top_k=3,
    btc_anchor=True,
    breadth_thresh=0.35,
    be_atr=1.2,
    trail_atr=2.0,
    sl_atr=2.0,
    leverage=1.5,
    use_inv_vol=True,
    filter_alpha=True
):
    if coins is None:
        coins = UNIVERSE_30[:12]  # Default to Top-12 liquid / high-alpha assets
        
    print(f"\n{'='*75}")
    print(f"🌟 Multi-Coin Vegas Z-Score Portfolio: {len(coins)} Coins ({tf}, Top-{top_k}) 🌟")
    print(f"Universe: {', '.join(coins)}")
    print(f"Risk Controls: BTC Anchor={btc_anchor}, Breadth={breadth_thresh}, BE Ratchet={be_atr}x, Trail={trail_atr}x, InvVol={use_inv_vol}")
    print(f"{'='*75}\n")

    # 1. Load Data
    dfs = {c: load_coin_data(c, tf) for c in coins}
    common_idx = dfs['BTC'].index
    for c in coins:
        common_idx = common_idx.intersection(dfs[c].index)
    for c in coins:
        dfs[c] = dfs[c].loc[common_idx].copy()

    # 2. Indicators via pure library functions
    btc_close = dfs['BTC']['Close']
    for c in coins:
        df = dfs[c]
        ema_fast, ema_slow, vegas_mid = calc_vegas_tunnel(df, 144, 169)
        ema_macro_f, _, _ = calc_vegas_macro_tunnel(df, 576, 676)
        ema_12 = talib.EMA(df['Close'], 12)
        
        vegas_top = np.maximum(ema_fast, ema_slow)
        vegas_bot = np.minimum(ema_fast, ema_slow)
        
        atr = calc_atr(df, 14)
        adx = calc_adx(df, 14)
        vol_sma = calc_sma(df['Volume'], 20)
        z_price = calc_zscore(df['Close'], 20)
        
        dist = df['Close'] - vegas_mid
        z_dist = (dist - dist.rolling(20).mean()) / (dist.rolling(20).std() + 1e-8)
        
        # 60-bar relative return vs BTC
        rel_alpha = df['Close'].pct_change(60) - btc_close.pct_change(60)
        
        df['ema_12'] = ema_12
        df['vegas_top'] = vegas_top
        df['vegas_bot'] = vegas_bot
        df['ema_macro'] = ema_macro_f
        df['atr'] = atr
        df['adx'] = adx
        df['z_price'] = z_price
        df['z_dist'] = z_dist
        df['rel_alpha'] = rel_alpha
        df['vol_confirm'] = df['Volume'] > (vol_sma * 0.85)
        df['is_bull'] = (df['Close'] > vegas_top) & (df['Close'] > ema_macro_f)

    # 3. Market Breadth & BTC Anchor
    bull_matrix = pd.DataFrame({c: dfs[c]['is_bull'] for c in coins}, index=common_idx)
    market_breadth = bull_matrix.mean(axis=1)
    btc_bull = (dfs['BTC']['Close'] > dfs['BTC']['vegas_bot']) & (dfs['BTC']['Close'] > dfs['BTC']['ema_macro'])

    # 4. Cross-Sectional Ranking Matrix (Z-Score + Relative Alpha)
    if filter_alpha:
        rank_score = pd.DataFrame({
            c: dfs[c]['z_price'] * (1.0 + dfs[c]['rel_alpha'].clip(-0.5, 0.5)) for c in coins
        }, index=common_idx)
    else:
        rank_score = pd.DataFrame({c: dfs[c]['z_price'] for c in coins}, index=common_idx)
    rank_matrix = rank_score.rank(axis=1, ascending=False)

    # 5. Signal Generation
    for c in coins:
        df = dfs[c]
        vegas_break = (df['Close'] > df['vegas_top']) & (df['ema_12'] > df['vegas_top'])
        macro_bull = df['Close'] > df['ema_macro']
        mom_ok = (df['z_price'] > 0.4) & (df['adx'] > 18.0)
        vol_ok = df['vol_confirm']
        breadth_ok = market_breadth >= breadth_thresh
        anchor_ok = btc_bull if (btc_anchor and c != 'BTC') else pd.Series(True, index=common_idx)
        top_k_ok = rank_matrix[c] <= top_k
        not_overextended = df['z_dist'] < 2.8
        alpha_ok = (df['rel_alpha'] > -0.05) if filter_alpha else pd.Series(True, index=common_idx)
        
        entry_cond = vegas_break & macro_bull & mom_ok & vol_ok & breadth_ok & anchor_ok & top_k_ok & not_overextended & alpha_ok
        entry_trigger = entry_cond & (~entry_cond.shift(1, fill_value=False))
        df['signal'] = entry_trigger.astype(int)

    # 6. Portfolio Execution & Signal Capture
    cash = 1000000.0
    initial_cash = 1000000.0
    positions = {}
    equity_curve = []
    trades = []
    raw_events = []
    fee_rate = 0.0005

    for i, t in enumerate(common_idx):
        if i < 600:
            continue
        current_prices = {c: dfs[c]['Close'].iloc[i] for c in coins}
        
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
                trades.append({
                    'time': t, 'symbol': c, 'type': 'EXIT_LONG',
                    'price': exec_p, 'reason': 'SL', 'pnl': pnl, 'fee': fee, 'qty': pos['qty']
                })
                raw_events.append({'time': t, 'symbol': c, 'target': 0.0, 'margin': pos['margin'], 'leverage': leverage})
                to_close.append(c)
                continue
                
            # Vegas Structural Exit
            if row['Close'] < row['vegas_bot']:
                exec_p = row['Close']
                pnl = (exec_p - pos['entry_price']) * pos['qty']
                fee = exec_p * pos['qty'] * fee_rate
                cash += (pos['qty'] * pos['entry_price'] / leverage) + pnl - fee
                trades.append({
                    'time': t, 'symbol': c, 'type': 'EXIT_LONG',
                    'price': exec_p, 'reason': 'VEGAS_EXIT', 'pnl': pnl, 'fee': fee, 'qty': pos['qty']
                })
                raw_events.append({'time': t, 'symbol': c, 'target': 0.0, 'margin': pos['margin'], 'leverage': leverage})
                to_close.append(c)
                continue
                
            # Profit Protection Ratchets
            if be_atr > 0 and price >= pos['entry_price'] + (be_atr * atr_v):
                be_sl = pos['entry_price'] + (0.15 * atr_v)
                if be_sl > pos['sl']:
                    pos['sl'] = be_sl
                    
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
            
            # Position sizing
            if use_inv_vol:
                atr_pct = dfs[c]['atr'].iloc[i] / current_prices[c]
                # Dynamic volatility sizing: scale inverse to ATR%
                target_notional = curr_equity * (0.025 / (sl_atr * atr_pct))
                max_notional = (curr_equity * 0.90 / top_k) * leverage
                notional = min(target_notional, max_notional)
                target_margin = notional / leverage
            else:
                target_margin = (curr_equity * 0.90 / top_k)
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
            
            initial_sl = entry_p - (sl_atr * dfs[c]['atr'].iloc[i])
            positions[c] = {
                'qty': qty,
                'entry_price': entry_p,
                'sl': initial_sl,
                'margin': target_margin,
                'entry_bar': i
            }
            trades.append({
                'time': t, 'symbol': c, 'type': 'BUY',
                'price': entry_p, 'reason': 'ENTRY', 'qty': qty, 'fee': fee, 'pnl': 0.0
            })
            raw_events.append({'time': t, 'symbol': c, 'target': 1.0, 'margin': target_margin, 'leverage': leverage})
            
        unrealized = sum((current_prices[pc] - p['entry_price']) * p['qty'] for pc, p in positions.items())
        margin_locked = sum(p['qty'] * p['entry_price'] / leverage for p in positions.values())
        equity_curve.append(cash + margin_locked + unrealized)

    eq_series = pd.Series(equity_curve)
    ret_pct = (eq_series.iloc[-1] / initial_cash - 1.0) * 100.0
    peak = eq_series.cummax()
    dd = (eq_series - peak) / peak
    mdd_pct = abs(dd.min()) * 100.0
    
    bar_rets = eq_series.pct_change().dropna()
    sharpe = (bar_rets.mean() / (bar_rets.std() + 1e-9)) * np.sqrt(2190) if bar_rets.std() > 0 else 0.0
    
    closed_trades = [t for t in trades if t['type'] == 'EXIT_LONG']
    tdf = pd.DataFrame(closed_trades)
    win_rate = (tdf['pnl'] > 0).mean() * 100.0 if not tdf.empty else 0.0
    gains = tdf[tdf['pnl'] > 0]['pnl'].sum() if not tdf.empty else 0.0
    losses = abs(tdf[tdf['pnl'] < 0]['pnl'].sum()) if not tdf.empty else 0.0
    pf = (gains / losses) if losses > 0 else 99.0

    print(f"\n--- Local Backtest Performance ---")
    print(f"Total Return:    +{ret_pct:.2f}% (Final Equity: ${eq_series.iloc[-1]:,.2f})")
    print(f"Max Drawdown:    {mdd_pct:.2f}%")
    print(f"Sharpe Ratio:    {sharpe:.3f}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print(f"Profit Factor:   {pf:.2f}")
    print(f"Total Trades:    {len(closed_trades)}")
    print(f"Total Signals:   {len(raw_events)}")

    return raw_events, coins, tf, ret_pct, sharpe, mdd_pct, eq_series.iloc[-1]

def submit_to_signal_strive(raw_events, coins, tf, strategy_name, top_k=3):
    api_key = _load_api_key()
    
    # Filter state flips to avoid redundant signals
    raw_events.sort(key=lambda x: x['time'])
    running_state = {}
    filtered_signals = []
    
    for e in raw_events:
        sym = f"{e['symbol']}USDT"
        tgt = int(e['target'])
        if running_state.get(sym) == tgt:
            continue
        running_state[sym] = tgt
        
        filtered_signals.append({
            'ts': int(pd.Timestamp(e['time']).value),  # nanoseconds
            'symbol': sym,
            'target': tgt,
            'strength': round(1.0 / top_k, 3),
            'margin': round(float(e['margin']), 2),
            'leverage': round(float(e['leverage']), 2),
        })

    payload = {
        'strategy': strategy_name,
        'resolution': tf,
        'start': '2021-01-01',
        'end': '2026-05-31',
        'signals': filtered_signals
    }

    endpoints = [
        'https://btest.abcz-tr.com/api/v1/signals',
        'http://47.237.70.198:5300/api/v1/signals'
    ]
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    print(f"\nPosting {len(filtered_signals)} filtered signals across {len(coins)} coins to Signal Strive API...")
    resp_data = None
    for ep in endpoints:
        try:
            print(f"Connecting to {ep}...")
            r = requests.post(ep, headers=headers, json=payload, timeout=300)
            if r.status_code == 200:
                resp_data = r.json()
                print(f"✅ Success from {ep}!")
                break
            elif r.status_code == 202:
                job = r.json()
                job_id = job.get('job_id')
                poll_url = f"https://btest.abcz-tr.com/api/v1/signals/jobs/{job_id}"
                print(f"⏳ Accepted as background job {job_id} (ETA {job.get('eta_seconds')}s). Polling...")
                for _ in range(30):
                    time.sleep(4)
                    try:
                        pr = requests.get(poll_url, headers=headers, timeout=15)
                        if pr.status_code == 200:
                            pj = pr.json()
                            st = pj.get('status')
                            prog = pj.get('progress_pct', 0)
                            print(f"   [Job {job_id}] status={st}, progress={prog}%")
                            if st == 'done' and pj.get('run_id'):
                                run_id = pj['run_id']
                                run_url = f"https://btest.abcz-tr.com/api/v1/runs/{run_id}"
                                rr = requests.get(run_url, headers=headers, timeout=15)
                                if rr.status_code == 200:
                                    resp_data = rr.json()
                                    print(f"✅ Run {run_id} fetched successfully!")
                                    break
                    except Exception as pe:
                        print(f"   Polling retry error: {pe}")
                if resp_data:
                    break
            else:
                print(f"Endpoint {ep} returned {r.status_code}: {r.text[:300]}")
        except Exception as e:
            print(f"Failed to connect to {ep}: {e}")

    if not resp_data:
        raise RuntimeError("Failed to submit to all Signal Strive endpoints.")

    # Save raw response
    ts_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_file = SIGNAL_REPLAY_DIR / f"vegas_{len(coins)}coin_portfolio_{ts_tag}.json"
    with open(out_file, 'w') as f:
        json.dump({'response': resp_data}, f, indent=2)
    print(f"Full response saved to {out_file}")

    # Parse and report
    data = resp_data.get('response', resp_data)
    run_id = data.get('run_id')
    scorecard = data.get('scorecard', {})
    sizing = data.get('sizing', {})
    run_a = sizing.get('run_a', {})
    run_b = sizing.get('run_b', {})
    
    overall_score = scorecard.get('overall_score')
    overall_grade = scorecard.get('overall_grade')
    headline = scorecard.get('headline', '')
    
    run_a_ret = run_a.get('total_return_pct')
    run_a_sharpe = run_a.get('sharpe')
    run_a_mdd = run_a.get('max_drawdown_pct')
    run_a_equity = run_a.get('final_equity_usd')

    run_b_ret = run_b.get('total_return_pct')
    run_b_sharpe = run_b.get('sharpe')
    run_b_mdd = run_b.get('max_drawdown_pct')
    run_b_equity = run_b.get('final_equity_usd')
    
    print("\n" + "="*65)
    print(f"🏆 SIGNAL STRIVE OFFICIAL EVALUATION: {strategy_name} 🏆")
    print("="*65)
    print(f"Run ID:        {run_id}")
    print(f"Overall Grade: {overall_grade} (Score: {overall_score})")
    print(f"Headline:      {headline}")
    print(f"Lens:          {scorecard.get('lens')} (Resolution: {tf})")
    print("-" * 65)
    print(f"Run A (Standard Sizing):")
    print(f"  Return:       +{run_a_ret}%")
    print(f"  Sharpe:       {run_a_sharpe}")
    print(f"  Max Drawdown: {run_a_mdd}%")
    print(f"  Final Equity: ${run_a_equity:,.2f}" if run_a_equity else f"  Final Equity: {run_a_equity}")
    print("-" * 65)
    print(f"Run B (Provider Margin & Leverage):")
    print(f"  Return:       +{run_b_ret}%")
    print(f"  Sharpe:       {run_b_sharpe}")
    print(f"  Max Drawdown: {run_b_mdd}%")
    print(f"  Final Equity: ${run_b_equity:,.2f}" if run_b_equity else f"  Final Equity: {run_b_equity}")
    print("="*65)

    # Append to runs.json
    try:
        with open(RUNS_FILE, 'r') as f:
            rf = json.load(f)
        runs_list = rf.get('runs', [])
        
        runs_list.append({
            "strategy_id": f"259_{len(coins)}COIN",
            "strategy_name": strategy_name,
            "run_id": run_id,
            "status": "SCORED",
            "symbols": [f"{c}USDT" for c in coins],
            "resolution": tf,
            "overall_score": overall_score,
            "overall_grade": overall_grade,
            "total_return_pct": run_a_ret,
            "sharpe": run_a_sharpe,
            "max_drawdown_pct": run_a_mdd,
            "final_equity_usd": run_a_equity,
            "lens": scorecard.get('lens'),
            "run_b_return_pct": run_b_ret,
            "run_b_sharpe": run_b_sharpe,
            "run_b_mdd_pct": run_b_mdd,
            "replayed_at_ns": data.get('replayed_at_ns')
        })
        
        with open(RUNS_FILE, 'w') as f:
            json.dump({"runs": runs_list}, f, indent=2)
        print(f"Appended run {run_id} to {RUNS_FILE}")
    except Exception as e:
        print(f"Failed to append to runs.json: {e}")

    return resp_data

def main():
    parser = argparse.ArgumentParser(description="Multi-Coin Vegas Z-Score Portfolio Submitter")
    parser.add_argument('--coins', type=int, default=12, help="Number of coins in universe (10 to 30)")
    parser.add_argument('--top_k', type=int, default=3, help="Max concurrent positions")
    parser.add_argument('--tf', type=str, default='4h', help="Timeframe (4h)")
    parser.add_argument('--no_submit', action='store_true', help="Only run local backtest without API POST")
    args = parser.parse_args()

    selected_coins = UNIVERSE_30[:args.coins]
    strat_name = f"VEGAS_{len(selected_coins)}COIN_PORTFOLIO_TOP{args.top_k}_{args.tf.upper()}"

    raw_events, coins, tf, ret, sh, mdd, fin_eq = run_multicoin_portfolio(
        coins=selected_coins,
        tf=args.tf,
        top_k=args.top_k,
        btc_anchor=True,
        breadth_thresh=0.40,
        be_atr=1.0,
        trail_atr=1.8,
        sl_atr=2.0,
        leverage=1.2,
        use_inv_vol=True,
        filter_alpha=True
    )

    if not args.no_submit:
        submit_to_signal_strive(raw_events, coins, tf, strat_name)

if __name__ == '__main__':
    main()
