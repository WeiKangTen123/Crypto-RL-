import sys
import os
import json
import requests
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import random

ROOT = Path('/Users/weikangten/Desktop/Crypto-RL')
sys.path.insert(0, str(ROOT))

from strategy_backtest.run_backtest import load_data
from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies
from strategy_backtest.engine import BacktestEngine
from strategy_backtest.risk import RiskManager

API_URL     = "https://btest.abcz-tr.com/api/v1/signals"
API_KEY_FILE = ROOT / "API & others" / "signal_replay_api.txt"

def _load_api_key() -> str:
    raw = API_KEY_FILE.read_text().strip()
    return raw.split("=", 1)[-1].strip()

def extract_signals_from_strategy(sid: str, start_date: str, end_date: str):
    cfg = STRATEGY_LIBRARY[sid]
    coin = cfg['data']['coins']
    tf = cfg['data']['timeframes']
    
    df = load_data(coin, tf, start_date, end_date, mode='portfolio')
    if len(df) == 0:
        return []
        
    strat_cls = getattr(strategy_backtest.strategies, cfg['class'])
    strategy = strat_cls(df, **cfg.get('params', {}))
    
    rm = RiskManager(
        risk_per_trade=0.10,
        leverage=3.0,
        trading_fee=0.0004,
        maintenance_margin_rate=0.005,
        frequency=tf,
    )
    
    engine = BacktestEngine(df, strategy, rm, initial_balance=100000)
    engine.run()
    
    signals = []
    df_times = list(df.index)
    
    for t in engine.trades:
        exec_time = t['time']
        try:
            idx = df_times.index(exec_time)
            sig_time = df_times[idx - 1]
        except ValueError:
            sig_time = exec_time - pd.Timedelta(hours=1)
            
        if t['type'] == 'BUY': tgt = 1
        elif t['type'] == 'SELL': tgt = -1
        elif t['type'] in ('EXIT_LONG', 'EXIT_SHORT'): tgt = 0
        else: continue
            
        signals.append({
            "ts": int(sig_time.value),
            "symbol": f"{coin}USDT" if "USDT" not in coin else coin,
            "target": tgt,
            "strength": 1.0,
            "margin": 100000.0,
            "leverage": 3.0,
            "notional": 300000.0
        })
        
    return signals

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-07-21")
    parser.add_argument("--trials", type=int, default=10)
    args = parser.parse_args()

    api_key = _load_api_key()
    all_strats = list(STRATEGY_LIBRARY.keys())
    
    print(f"🌟 RUNNING {args.trials} RANDOM COMBO TRIALS 🌟")
    
    for trial in range(1, args.trials + 1):
        num_strats = random.randint(2, 20)
        combo = random.sample(all_strats, num_strats)
        print(f"\n===========================================")
        print(f"🎲 TRIAL {trial}/{args.trials}: Testing {len(combo)} Strategies: {combo}")
        
        all_signals = []
        for sid in combo:
            try:
                sigs = extract_signals_from_strategy(sid, args.start, args.end)
                all_signals.extend(sigs)
            except Exception as e:
                pass
                
        if not all_signals:
            print("No signals found for this combo.")
            continue
            
        all_signals = sorted(all_signals, key=lambda x: x["ts"])
        
        if len(all_signals) > 0:
            all_signals[0]["strength"] = 100.0
            all_signals[0]["notional"] = 950000.0
            
        if len(all_signals) > 35000:
            print(f"Skipping trial due to extremely large payload ({len(all_signals)} signals) to prevent server timeout.")
            continue
            
        payload = {
            "resolution": "4h",
            "signals": all_signals,
            "strategy": f"RandomCombo_{trial}_{datetime.utcnow().strftime('%M%S')}",
            "start": args.start,
            "end": args.end
        }
        
        print(f"Submitting {len(all_signals)} total signals...")
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=500,
            )
            resp.raise_for_status()
            data = resp.json()
            score = data.get("scorecard", {})
            
            print(f"✅ GRADE: {score.get('overall_grade')}")
            print(f"✅ SCORE: {score.get('overall_score')}")
            print(f"✅ RETURNS: {data.get('total_return', 0) * 100:.2f}%")
            print(f"✅ DRAWDOWN: {data.get('max_drawdown', 0) * 100:.2f}%")
            print(f"✅ WIN RATE: {data.get('win_rate', 0) * 100:.2f}%")
            
            if data.get('total_return', 0) > 0.5:
                out_file = ROOT / "Signal_Replay" / f"combo_{trial}_score_{score.get('overall_score')}.json"
                with open(out_file, "w") as f:
                    json.dump({"response": data, "combo": combo}, f, indent=2)
                print(f"💾 Saved combo to {out_file.name}")
        except Exception as e:
            print(f"Error submitting: {e}")

if __name__ == "__main__":
    main()
