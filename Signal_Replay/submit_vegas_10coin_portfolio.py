import sys
import os
import json
import requests
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import talib

ROOT = Path('/Users/weikangten/Desktop/Crypto-RL')
sys.path.insert(0, str(ROOT))

from strategy_backtest.run_backtest import load_data
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

COINS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOT', 'LINK', 'AAVE']

def _load_api_key() -> str:
    raw = API_KEY_FILE.read_text().strip()
    return raw.split('=', 1)[-1].strip()

def run_10coin_portfolio(
    tf='4h', top_k=3,
    start_date='2021-01-01', end_date='2026-05-31',
    btc_anchor=True, breakeven_atr=1.2, trail_atr=2.0,
    breadth_thresh=0.4, sl_atr_mult=2.0, leverage=1.5
):
    print(f"\n🌟 Running 10-Coin Vegas Z-Score Portfolio ({tf}, Top-{top_k}, BTC-Anchor={btc_anchor}) 🌟")
    
    # 1. Load data
    dfs = {}
    for c in COINS:
        dfs[c] = load_data(c, tf, start_date, end_date, mode='portfolio')

    common_idx = dfs['BTC'].index
    for c in COINS:
        common_idx = common_idx.intersection(dfs[c].index)
    for c in COINS:
        dfs[c] = dfs[c].loc[common_idx].copy()

    # 2. Indicators via pure library functions
    for c in COINS:
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
        
        df['ema_12'] = ema_12
        df['vegas_top'] = vegas_top
        df['vegas_bot'] = vegas_bot
        df['ema_macro'] = ema_macro_f
        df['atr'] = atr
        df['adx'] = adx
        df['z_price'] = z_price
        df['z_dist'] = z_dist
        df['vol_confirm'] = df['Volume'] > (vol_sma * 0.85)
        df['is_bull'] = (df['Close'] > vegas_top) & (df['Close'] > ema_macro_f)

    # 3. Market Breadth & BTC Anchor
    bull_matrix = pd.DataFrame({c: dfs[c]['is_bull'] for c in COINS}, index=common_idx)
    market_breadth = bull_matrix.mean(axis=1)
    
    btc_bull = (dfs['BTC']['Close'] > dfs['BTC']['vegas_bot']) & (dfs['BTC']['Close'] > dfs['BTC']['ema_macro'])
    
    # 4. Cross-Sectional Ranking Matrix (Z-Score)
    z_matrix = pd.DataFrame({c: dfs[c]['z_price'] for c in COINS}, index=common_idx)
    rank_matrix = z_matrix.rank(axis=1, ascending=False)

    # 5. Signals
    for c in COINS:
        df = dfs[c]
        vegas_break = (df['Close'] > df['vegas_top']) & (df['ema_12'] > df['vegas_top'])
        macro_bull = df['Close'] > df['ema_macro']
        mom_ok = (df['z_price'] > 0.4) & (df['adx'] > 18.0)
        vol_ok = df['vol_confirm']
        breadth_ok = market_breadth >= breadth_thresh
        anchor_ok = btc_bull if (btc_anchor and c != 'BTC') else pd.Series(True, index=common_idx)
        top_k_ok = rank_matrix[c] <= top_k
        not_overextended = df['z_dist'] < 2.8
        
        entry_cond = vegas_break & macro_bull & mom_ok & vol_ok & breadth_ok & anchor_ok & top_k_ok & not_overextended
        entry_trigger = entry_cond & (~entry_cond.shift(1, fill_value=False))
        
        signal = np.zeros(len(df), dtype=int)
        signal[entry_trigger.fillna(False)] = 1
        df['signal'] = signal

    # 6. Portfolio Simulation & Signal Capture
    cash = 1000000.0 # $1M base capital
    initial_cash = 1000000.0
    positions = {}
    equity_curve = []
    trades = []
    raw_events = [] # For Signal Strive: {ts, symbol, target, strength, margin, leverage}
    fee_rate = 0.0005

    for i, t in enumerate(common_idx):
        current_prices = {c: dfs[c]['Close'].iloc[i] for c in COINS}
        
        # 1. Update/Check Exits
        to_close = []
        for c, pos in list(positions.items()):
            row = dfs[c].iloc[i]
            price = current_prices[c]
            sl = pos['sl']
            atr = row['atr']
            
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
                
            # Structural Vegas Exit
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
                
            # Profit Protection Ratchet:
            if breakeven_atr > 0 and price >= pos['entry_price'] + (breakeven_atr * atr):
                be_sl = pos['entry_price'] + (0.1 * atr)
                if be_sl > pos['sl']:
                    pos['sl'] = be_sl
                    
            if trail_atr > 0 and price >= pos['entry_price'] + (2.5 * atr):
                t_sl = price - (trail_atr * atr)
                if t_sl > pos['sl']:
                    pos['sl'] = t_sl

        for c in to_close:
            del positions[c]
            
        # 2. Entries
        candidates = [c for c in COINS if dfs[c]['signal'].iloc[i] == 1 and c not in positions]
        candidates.sort(key=lambda c: dfs[c]['z_price'].iloc[i], reverse=True)
        
        for c in candidates:
            if len(positions) >= top_k:
                break
                
            unrealized = sum((current_prices[pos_c] - p['entry_price']) * p['qty'] for pos_c, p in positions.items())
            margin_locked = sum(p['qty'] * p['entry_price'] / leverage for p in positions.values())
            curr_equity = cash + margin_locked + unrealized
            
            target_margin = (curr_equity * 0.90 / top_k)
            if cash < target_margin:
                target_margin = max(0, cash * 0.85)
                
            if target_margin < 1000:
                continue
                
            entry_p = current_prices[c]
            notional = target_margin * leverage
            qty = notional / entry_p
            fee = notional * fee_rate
            
            cash -= (target_margin + fee)
            
            atr = dfs[c]['atr'].iloc[i]
            initial_sl = entry_p - (sl_atr_mult * atr)
            
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
            
        unrealized = sum((current_prices[pos_c] - p['entry_price']) * p['qty'] for pos_c, p in positions.items())
        margin_locked = sum(p['qty'] * p['entry_price'] / leverage for p in positions.values())
        equity = cash + margin_locked + unrealized
        equity_curve.append(equity)

    m = compute_metrics(
        equity=equity_curve,
        initial_balance=initial_cash,
        timestamps=common_idx,
        trades=trades
    )
    num = _extract_numeric(m)
    print(f"Local Trades: {num.get('Total Trades')} | Sharpe: {num.get('Sharpe Ratio', 0):.2f} | Return: {num.get('Total Return', 0):.1f}% | MDD: {num.get('Max Drawdown %', 0):.1f}% | PF: {num.get('Profit Factor', 0):.2f} | WinRate: {m.get('Win Rate')}")
    
    return raw_events, m

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--top_k', type=int, default=3)
    parser.add_argument('--leverage', type=float, default=1.5)
    parser.add_argument('--dry_run', action='store_true')
    args = parser.parse_args()

    events, m = run_10coin_portfolio(tf='4h', top_k=args.top_k, leverage=args.leverage)
    
    print(f"\nBuilding Signal Replay payload from {len(events)} events...")
    
    # Sort events chronologically and eliminate redundant state updates per symbol
    events = sorted(events, key=lambda x: x['time'])
    filtered_signals = []
    running_state = {}
    
    for e in events:
        sym = f"{e['symbol']}USDT"
        tgt = e['target']
        if running_state.get(sym) == tgt:
            continue
        running_state[sym] = tgt
        
        filtered_signals.append({
            'ts': int(e['time'].value), # ns
            'symbol': sym,
            'target': tgt,
            'strength': round(1.0 / args.top_k, 3),
            'margin': round(e['margin'], 2),
            'leverage': float(e['leverage']),
        })
        
    print(f"Final Signal Count: {len(filtered_signals)} signals across 10 coins.")
    
    payload = {
        'strategy': f"VEGAS_10COIN_PORTFOLIO_TOP{args.top_k}_4H",
        'resolution': '4h',
        'start': '2021-01-01',
        'end': '2026-05-31',
        'signals': filtered_signals
    }
    
    if args.dry_run:
        print("DRY RUN: Payload created successfully. First signal:")
        print(json.dumps(filtered_signals[0], indent=2))
        return
        
    api_key = _load_api_key()
    endpoints = [
        'https://btest.abcz-tr.com/api/v1/signals',
        'http://47.237.70.198:5300/api/v1/signals'
    ]
    
    resp_data = None
    for url in endpoints:
        try:
            print(f"Submitting payload to {url}...")
            resp = requests.post(
                url,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=300
            )
            resp.raise_for_status()
            resp_data = resp.json()
            break
        except Exception as e:
            print(f"Submission to {url} failed: {e}")
            
    if not resp_data:
        print("Failed to submit to all endpoints.")
        return
        
    out_file = SIGNAL_REPLAY_DIR / f"vegas_10coin_portfolio_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, 'w') as f:
        json.dump({'response': resp_data}, f, indent=2)
    print(f"\nSaved Signal Strive response to {out_file}!")
    
    scorecard = resp_data.get('scorecard', {})
    sizing = resp_data.get('sizing', {})
    run_a = sizing.get('run_a', {})
    run_b = sizing.get('run_b', {})
    
    print("\n" + "="*60)
    print("🏆 SIGNAL STRIVE OFFICIAL EVALUATION 🏆")
    print("="*60)
    print(f"Overall Grade   : {scorecard.get('overall_grade')}")
    print(f"Overall Score   : {scorecard.get('overall_score')}")
    print(f"Headline        : {scorecard.get('headline')}")
    print(f"Run A Return    : {run_a.get('total_return', 0)*100:.2f}%")
    print(f"Run A Sharpe    : {run_a.get('sharpe', 0):.3f}")
    print(f"Run A Max DD    : {run_a.get('max_drawdown', 0)*100:.2f}%")
    print(f"Run A Final Eq  : ${run_a.get('final_equity_usd', 0):,.2f}")
    if run_b:
        print(f"Run B Return    : {run_b.get('total_return', 0)*100:.2f}%")
        print(f"Run B Sharpe    : {run_b.get('sharpe', 0):.3f}")
        print(f"Run B Max DD    : {run_b.get('max_drawdown', 0)*100:.2f}%")
        print(f"Run B Final Eq  : ${run_b.get('final_equity_usd', 0):,.2f}")
    print("="*60)
    
    # Append to runs.json
    try:
        with open(RUNS_FILE, 'r') as f:
            runs_data = json.load(f)
        runs_list = runs_data['runs'] if isinstance(runs_data, dict) and 'runs' in runs_data else runs_data
        
        entry = {
            'strategy_id': '259_10COIN',
            'strategy_name': payload['strategy'],
            'run_id': resp_data.get('run_id'),
            'status': 'SCORED',
            'symbols': resp_data.get('symbols', COINS),
            'resolution': '4h',
            'overall_score': scorecard.get('overall_score'),
            'overall_grade': scorecard.get('overall_grade'),
            'total_return_pct': round(run_a.get('total_return', 0) * 100, 2),
            'sharpe': round(run_a.get('sharpe', 0), 3),
            'max_drawdown_pct': round(run_a.get('max_drawdown', 0) * 100, 2),
            'final_equity_usd': round(run_a.get('final_equity_usd', 0), 2),
            'n_fills': run_a.get('n_fills'),
            'lens': scorecard.get('lens'),
            'run_b_return_pct': round(run_b.get('total_return', 0) * 100, 2) if run_b else None,
            'run_b_sharpe': round(run_b.get('sharpe', 0), 3) if run_b else None,
            'replayed_at_ns': resp_data.get('replayed_at_ns')
        }
        runs_list.append(entry)
        with open(RUNS_FILE, 'w') as f:
            json.dump({'runs': runs_list} if isinstance(runs_data, dict) and 'runs' in runs_data else runs_list, f, indent=2)
        print("Updated runs.json successfully!")
    except Exception as e:
        print(f"Failed to update runs.json: {e}")

if __name__ == '__main__':
    main()
