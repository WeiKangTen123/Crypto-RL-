#!/usr/bin/env python3
"""
submit_vegas_macro_etf_portfolio.py — Lead Architect / Crypto-RL
Submits the Macro Market Map & Spot Bitcoin ETF Enhanced Multi-Coin Vegas Portfolio Strategy
to the Signal Strive / Signal Replay API (https://btest.abcz-tr.com/api/v1/signals).

Combines:
1. Vegas Tunnel (EMA 144/169) & Macro Tunnel (EMA 576/676)
2. Statistical Z-Score & Relative Alpha Cross-Sectional Ranking
3. Cross-Asset Macro Market Map (SPY, DXY, VIX, JPY) Lead-Lag Regime & Panic Circuit Breaker
4. Spot Bitcoin ETF Institutional Flow Engine (IBIT, FBTC) Outflow Alert
5. Dynamic Inverse-Volatility Risk Parity Sizing scaled by Macro Confidence
6. Two-Stage Ratchet Trade Management (Breakeven + Chandelier Trail + Macro Shock Exit)
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
    calc_sma,
    calc_macro_regime_index,
    calc_etf_flow_proxy
)

SIGNAL_REPLAY_DIR = ROOT / 'Signal_Replay'
API_KEY_FILE = ROOT / 'API & others' / 'signal_replay_api.txt'
RUNS_FILE = SIGNAL_REPLAY_DIR / 'runs.json'
DATASET_ROOT = ROOT / 'dataset'

COINS_10 = ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'AVAX', 'ADA', 'BCH', 'XRP', 'LINK']
COINS_12 = ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'AVAX', 'ADA', 'BCH', 'XRP', 'LINK', 'DOT', 'LTC']

def _load_api_key() -> str:
    raw = API_KEY_FILE.read_text().strip()
    return raw.split('=', 1)[-1].strip()

def load_coin_data(coin: str, tf: str = '4h') -> pd.DataFrame:
    p = DATASET_ROOT / coin / tf / 'spot_ohlcv.parquet'
    if not p.exists():
        raise FileNotFoundError(f"Parquet missing for {coin} at {p}")
    df = pd.read_parquet(p)
    t_col = 'open_time' if 'open_time' in df.columns else 'timestamp'
    df[t_col] = pd.to_datetime(df[t_col])
    df = df.sort_values(t_col).drop_duplicates(t_col).set_index(t_col)
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

def run_portfolio_simulation(
    coins,
    tf='4h',
    top_k=3,
    macro_min_score=0.40,
    breadth_thresh=0.35,
    be_atr=1.2,
    trail_atr=2.0,
    sl_atr=2.0,
    leverage=1.5,
    use_inv_vol=True
):
    print(f"\n{'='*80}")
    print(f"🌟 Multi-Coin Vegas Macro & ETF Portfolio: {len(coins)} Coins ({tf}, Top-{top_k}) 🌟")
    print(f"Universe: {', '.join(coins)}")
    print(f"Filters: Macro Gate={macro_min_score}, Breadth={breadth_thresh}, BE={be_atr}x, Trail={trail_atr}x, InvVol={use_inv_vol}")
    print(f"{'='*80}\n")

    # 1. Load Coin Data
    dfs = {c: load_coin_data(c, tf) for c in coins}
    common_idx = dfs['BTC'].index
    for c in coins:
        common_idx = common_idx.intersection(dfs[c].index)
    for c in coins:
        dfs[c] = dfs[c].loc[common_idx].copy()

    # 2. Load Macro & Spot ETF Data
    macro_dfs = {}
    for m in ['SPY', 'DXY', 'VIX', 'JPY', 'IBIT', 'FBTC']:
        df_m = load_coin_data(m, tf)
        macro_dfs[m] = df_m.reindex(common_idx).ffill().bfill()

    # 3. Compute Macro Regime Index & ETF Institutional Flow Proxy
    macro_score, macro_veto = calc_macro_regime_index(
        macro_dfs['SPY'], macro_dfs['DXY'], macro_dfs['VIX'], macro_dfs['JPY']
    )
    etf_score, etf_outflow_alert = calc_etf_flow_proxy(
        macro_dfs['IBIT'], macro_dfs['FBTC']
    )

    # 4. Indicators per coin via pure library functions
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

    # 5. Market Breadth & BTC Anchor
    bull_matrix = pd.DataFrame({c: dfs[c]['is_bull'] for c in coins}, index=common_idx)
    market_breadth = bull_matrix.mean(axis=1)
    btc_bull = (dfs['BTC']['Close'] > dfs['BTC']['vegas_bot']) & (dfs['BTC']['Close'] > dfs['BTC']['ema_macro'])

    # 6. Cross-Sectional Ranking Matrix (Z-Score + Relative Alpha)
    rank_score = pd.DataFrame({
        c: dfs[c]['z_price'] * (1.0 + dfs[c]['rel_alpha'].clip(-0.5, 0.5)) for c in coins
    }, index=common_idx)
    rank_matrix = rank_score.rank(axis=1, ascending=False)

    # 7. Signal Generation with Macro & ETF Gates
    for c in coins:
        df = dfs[c]
        vegas_break = (df['Close'] > df['vegas_top']) & (df['ema_12'] > df['vegas_top'])
        macro_bull = df['Close'] > df['ema_macro']
        mom_ok = (df['z_price'] > 0.4) & (df['adx'] > 18.0)
        vol_ok = df['vol_confirm']
        breadth_ok = market_breadth >= breadth_thresh
        anchor_ok = btc_bull if c != 'BTC' else pd.Series(True, index=common_idx)
        top_k_ok = rank_matrix[c] <= top_k
        not_overextended = df['z_dist'] < 2.8
        alpha_ok = df['rel_alpha'] > -0.05

        macro_pass = (~macro_veto) & (macro_score >= macro_min_score)
        etf_pass = ~etf_outflow_alert

        entry_cond = (
            vegas_break & macro_bull & mom_ok & vol_ok & breadth_ok &
            anchor_ok & top_k_ok & not_overextended & alpha_ok & macro_pass & etf_pass
        )
        entry_trigger = entry_cond & (~entry_cond.shift(1, fill_value=False))
        df['signal'] = entry_trigger.astype(int)

    # 8. Portfolio Execution Simulation & Event Generation
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
        is_panic = bool(macro_veto.iloc[i])
        is_etf_dump = bool(etf_outflow_alert.iloc[i])

        # A. Check Exits
        to_close = []
        for c, pos in list(positions.items()):
            row = dfs[c].iloc[i]
            price = current_prices[c]
            sl = pos['sl']
            atr_v = row['atr']

            # Profit Protection: If macro panic or ETF outflow alert fires, ratchet profit lock to Breakeven
            if (is_panic or is_etf_dump) and price > pos['entry_price']:
                be_sl = pos['entry_price'] + (0.15 * atr_v)
                if be_sl > pos['sl']:
                    pos['sl'] = be_sl

            # Hard Stop Loss hit
            if row['Low'] <= sl:
                exec_p = sl
                pnl = (exec_p - pos['entry_price']) * pos['qty']
                fee = exec_p * pos['qty'] * fee_rate
                cash += (pos['qty'] * pos['entry_price'] / leverage) + pnl - fee
                trades.append({
                    'time': t, 'symbol': c, 'type': 'EXIT_LONG',
                    'price': exec_p, 'reason': 'SL', 'pnl': pnl, 'fee': fee, 'qty': pos['qty']
                })
                raw_events.append({'time': t, 'symbol': c, 'target': 0.0, 'margin': pos['margin'], 'leverage': leverage, 'strength': 0.0})
                to_close.append(c)
                continue

            # Structural Vegas Tunnel Breakdown Exit
            if row['Close'] < row['vegas_bot']:
                exec_p = row['Close']
                pnl = (exec_p - pos['entry_price']) * pos['qty']
                fee = exec_p * pos['qty'] * fee_rate
                cash += (pos['qty'] * pos['entry_price'] / leverage) + pnl - fee
                trades.append({
                    'time': t, 'symbol': c, 'type': 'EXIT_LONG',
                    'price': exec_p, 'reason': 'VEGAS_EXIT', 'pnl': pnl, 'fee': fee, 'qty': pos['qty']
                })
                raw_events.append({'time': t, 'symbol': c, 'target': 0.0, 'margin': pos['margin'], 'leverage': leverage, 'strength': 0.0})
                to_close.append(c)
                continue

            # ETF Outflow Alert: Tighten profit lock immediately
            if is_etf_dump and price > pos['entry_price']:
                be_sl = pos['entry_price'] + (0.15 * atr_v)
                if be_sl > pos['sl']:
                    pos['sl'] = be_sl

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
            m_score_val = float(macro_score.iloc[i])
            m_mult = np.clip(m_score_val, 0.60, 1.15)

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
            strength_val = round(float(np.clip(m_score_val / top_k, 0.15, 0.50)), 3)
            raw_events.append({
                'time': t, 'symbol': c, 'target': 1.0,
                'margin': target_margin, 'leverage': leverage, 'strength': strength_val
            })

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
    print(f"Total Events:    {len(raw_events)}")

    return raw_events, coins, tf, ret_pct, sharpe, mdd_pct, eq_series.iloc[-1]

def submit_to_signal_strive(raw_events, coins, tf, strategy_name, top_k=3):
    api_key = _load_api_key()

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
            'ts': int(pd.Timestamp(e['time']).value),
            'symbol': sym,
            'target': tgt,
            'strength': float(e.get('strength', round(1.0 / top_k, 3))),
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

    print(f"\nPosting {len(filtered_signals)} filtered signals across {len(coins)} coins to Signal Strive API...")
    resp_data = None
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    for ep in endpoints:
        try:
            print(f"Connecting to {ep}...")
            r = requests.post(ep, json=payload, headers=headers, timeout=60)
            if r.status_code == 200:
                resp_data = r.json()
                print(f"--> Immediate 200 OK received from {ep}!")
                break
            elif r.status_code == 202:
                resp_data = r.json()
                print(f"--> Async 202 Accepted received: {resp_data}")
                job_id = resp_data.get('job_id')
                poll_url = f"{ep}/jobs/{job_id}"
                print(f"Polling job {job_id} at {poll_url}...")
                for attempt in range(60):
                    time.sleep(3)
                    pr = requests.get(poll_url, headers=headers, timeout=15)
                    if pr.status_code == 200:
                        pj = pr.json()
                        st = pj.get('status')
                        print(f"  [Attempt {attempt+1}] Job status: {st}")
                        if st == 'done':
                            run_id = pj.get('run_id')
                            print(f"  --> Job complete! Fetching run details for {run_id}...")
                            run_url = f"{ep.rsplit('/', 1)[0]}/runs/{run_id}"
                            rr = requests.get(run_url, headers=headers, timeout=15)
                            if rr.status_code == 200:
                                resp_data = rr.json()
                                break
                        elif st == 'failed':
                            print(f"  --> Job failed: {pj}")
                            break
                if resp_data and ('metrics' in resp_data or 'run_a' in resp_data or 'run_b' in resp_data or 'scorecard' in resp_data):
                    break
            else:
                print(f"--> Response {r.status_code}: {r.text[:200]}")
        except Exception as ex:
            print(f"--> Connection failed to {ep}: {ex}")

    if not resp_data:
        print("ERROR: Failed to obtain valid response from Signal Strive endpoints.")
        return None

    return resp_data

def catalog_results(strategy_id, strategy_name, coins, tf, local_ret, local_sharpe, local_mdd, resp):
    run_id = resp.get('run_id', f"sr_macro_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    scorecard = resp.get('scorecard', {})
    overall_score = scorecard.get('overall_score', resp.get('overall_score', 0))
    overall_grade = scorecard.get('overall_grade', resp.get('grade', 'N/A'))
    headline = scorecard.get('headline', '')

    # Run A metrics (top-level or run_a)
    ra_ret = round(float(resp.get('total_return', 0)) * 100.0, 2)
    ra_sharpe = round(float(resp.get('sharpe', 0)), 3)
    ra_mdd = round(float(resp.get('max_drawdown', 0)) * 100.0, 2)
    ra_equity = round(float(resp.get('final_equity_usd', 0)), 2)

    # Run B metrics (from report_b)
    rep_b = resp.get('report_b', {})
    tiles_b = rep_b.get('tiles', {})
    eq_b_list = rep_b.get('equity_curve', [])
    if eq_b_list:
        df_eq = pd.DataFrame(eq_b_list)
        rb_ret = round(float((df_eq['e'].iloc[-1] / df_eq['e'].iloc[0] - 1.0) * 100.0), 2)
        peak_b = df_eq['e'].cummax()
        rb_mdd = round(float(abs(((df_eq['e'] - peak_b) / peak_b).min()) * 100.0), 2)
        rets_b = df_eq['e'].pct_change().dropna()
        rb_sharpe = round(float((rets_b.mean() / (rets_b.std() + 1e-9)) * (365 * 6)**0.5), 3)
        rb_equity = round(float(df_eq['e'].iloc[-1]), 2)
    else:
        rb_ret, rb_mdd, rb_sharpe, rb_equity = 0.0, 0.0, 0.0, 0.0

    entry = {
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "run_id": run_id,
        "status": "SCORED",
        "symbols": [f"{c}USDT" for c in coins],
        "resolution": tf,
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "headline": headline,
        "total_return_pct": ra_ret,
        "sharpe": ra_sharpe,
        "max_drawdown_pct": ra_mdd,
        "final_equity_usd": ra_equity,
        "lens": scorecard.get('lens'),
        "run_b_return_pct": rb_ret,
        "run_b_sharpe": rb_sharpe,
        "run_b_mdd_pct": rb_mdd,
        "run_b_final_equity_usd": rb_equity,
        "run_b_profit_factor": round(float(tiles_b.get('profit_factor', 0)), 2),
        "run_b_cost_ratio": round(float(tiles_b.get('cost_ratio', 0)) * 100.0, 1),
        "run_b_hit_rate": round(float(tiles_b.get('hit_rate', 0)) * 100.0, 1),
        "replayed_at_ns": resp.get('replayed_at_ns')
    }

    print("\n" + "="*65)
    print(f"🏆 SIGNAL STRIVE OFFICIAL EVALUATION: {strategy_name} 🏆")
    print("="*65)
    print(f"Run ID:        {run_id}")
    print(f"Overall Grade: {overall_grade} (Score: {overall_score})")
    print(f"Headline:      {headline}")
    print("-" * 65)
    print(f"Run A (Standard Sizing):")
    print(f"  Return:       +{ra_ret}%")
    print(f"  Sharpe:       {ra_sharpe}")
    print(f"  Max Drawdown: {ra_mdd}%")
    print(f"  Final Equity: ${ra_equity:,.2f}")
    print("-" * 65)
    print(f"Run B (Provider Margin & Leverage):")
    print(f"  Return:       +{rb_ret}%")
    print(f"  Sharpe:       {rb_sharpe}")
    print(f"  Max Drawdown: {rb_mdd}%")
    print(f"  Final Equity: ${rb_equity:,.2f}")
    print(f"  Profit Factor:{tiles_b.get('profit_factor', 'N/A')}")
    print(f"  Cost Ratio:   {tiles_b.get('cost_ratio', 'N/A')}")
    print("="*65)

    # Load existing runs
    runs_list = []
    if RUNS_FILE.exists():
        try:
            with open(RUNS_FILE, 'r') as f:
                rf = json.load(f)
            runs_list = rf.get('runs', [])
        except Exception:
            runs_list = []

    # Update or append
    runs_list = [r for r in runs_list if r.get('run_id') != run_id]
    runs_list.append(entry)
    with open(RUNS_FILE, 'w') as f:
        json.dump({"runs": runs_list}, f, indent=2)
    print(f"\n[CATALOG] Successfully recorded run {run_id} into {RUNS_FILE}")
    return entry

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy-id', type=str, default='261', choices=['261', '262'])
    parser.add_argument('--submit', action='store_true', help='Submit directly to Signal Strive API')
    args = parser.parse_args()

    if args.strategy_id == '261':
        coins = COINS_10
        strat_name = 'VEGAS_MACRO_ETF_10COIN_PORTFOLIO_4H'
    else:
        coins = COINS_12
        strat_name = 'VEGAS_MACRO_ETF_12COIN_PORTFOLIO_4H'

    events, c_list, tf, ret, sh, mdd, fin_eq = run_portfolio_simulation(
        coins=coins,
        tf='4h',
        top_k=3,
        macro_min_score=0.40,
        breadth_thresh=0.35,
        be_atr=1.2,
        trail_atr=2.0,
        sl_atr=2.0,
        leverage=1.5,
        use_inv_vol=True
    )

    if args.submit:
        resp = submit_to_signal_strive(events, c_list, tf, strat_name, top_k=3)
        if resp:
            cat = catalog_results(args.strategy_id, strat_name, c_list, tf, ret, sh, mdd, resp)

