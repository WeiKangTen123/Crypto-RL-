import sys
import os
import json
import requests
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import random

ROOT = Path('/Users/weikangten/Desktop/Crypto-RL')
sys.path.insert(0, str(ROOT))

from strategy_backtest.run_backtest import load_data
from strategy_backtest.settings import STRATEGY_LIBRARY
import strategy_backtest.strategies

API_URL     = "https://btest.abcz-tr.com/api/v1/signals"
API_KEY_FILE = ROOT / "API & others" / "signal_replay_api.txt"

def _load_api_key() -> str:
    raw = API_KEY_FILE.read_text().strip()
    return raw.split("=", 1)[-1].strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-07-21")
    args = parser.parse_args()

    # Timeframe and coins - totally random
    tfs = ["15m", "30m", "1h", "4h", "1d"]
    chosen_tf = random.choice(tfs)
    all_coins = ["BTC", "ETH", "BNB", "SOL", "XRP"]
    num_coins = random.randint(1, len(all_coins))
    chosen_coins = random.sample(all_coins, num_coins)

    print(f"🎲 RANDOM SELECTION: Timeframe = {chosen_tf}, Coins = {chosen_coins}")

    # Pick 4-8 random strategies from STRATEGY_LIBRARY that can run on this TF (or we force run them on this TF)
    # The strategies don't actually care what TF the data is, they just calculate indicators.
    strat_keys = list(STRATEGY_LIBRARY.keys())
    num_strats = random.randint(4, 8)
    chosen_strats = random.sample(strat_keys, num_strats)
    print(f"🎲 RANDOM STRATEGIES: {chosen_strats}")

    yearly_chunks = {}

    for coin in chosen_coins:
        print(f"\n--- Processing Coin: {coin} ---")
        try:
            df = load_data(coin, chosen_tf, args.start, args.end, mode="per_coin")
        except Exception as e:
            print(f"Data load failed for {coin}: {e}")
            continue
            
        if len(df) == 0:
            print(f"No data for {coin}")
            continue

        signals_list = []
        for sid in chosen_strats:
            cfg = STRATEGY_LIBRARY[sid]
            strat_cls_name = cfg['class']
            if not hasattr(strategy_backtest.strategies, strat_cls_name):
                print(f"Class {strat_cls_name} not found, skipping...")
                continue
                
            strat_cls = getattr(strategy_backtest.strategies, strat_cls_name)
            try:
                strategy = strat_cls(df, **cfg.get('params', {}))
                df_sig = strategy.generate_signals()
                signals_list.append(df_sig['signal'].copy())
            except Exception as e:
                print(f"Strategy {sid} failed on {coin}: {e}")
                
        if not signals_list:
            print(f"No valid strategies for {coin}")
            continue
            
        combined = pd.concat(signals_list, axis=1)
        mean_signal = combined.mean(axis=1)
        
        position = 0
        entry_price = 0.0
        
        # Random exit rules
        tp_pct = random.uniform(0.02, 0.10)
        sl_pct = random.uniform(0.01, 0.05)
        
        for i in range(len(df)):
            c = float(df['Close'].iloc[i])
            ts = int(df.index[i].value)
            year = df.index[i].year
            sig_val = mean_signal.iloc[i]
            
            target_pos = 0
            # Random threshold between 0.1 and 0.4
            thresh = random.uniform(0.1, 0.4)
            if sig_val >= thresh:
                target_pos = 1
            elif sig_val <= -thresh:
                target_pos = -1

            if position != 0:
                pnl_pct = (c - entry_price) / entry_price if position == 1 else (entry_price - c) / entry_price
                if pnl_pct >= tp_pct or pnl_pct <= -sl_pct:
                    target_pos = 0

            if target_pos != position:
                if target_pos != 0:
                    entry_price = c
                position = target_pos
                
                conf = float(abs(sig_val))
                
                # Random margin/leverage logic
                trade_margin = float(random.choice([1000, 5000, 10000, 50000]))
                trade_lev = float(random.choice([1.0, 2.0, 3.0, 5.0, 10.0]))
                notional = trade_margin * trade_lev
                
                sig = {
                    "ts": ts,
                    "symbol": f"{coin}USDT",
                    "target": float(position),
                    "margin": trade_margin,
                    "leverage": trade_lev,
                    "notional": notional,
                    "strength": conf,
                }
                
                if position == 1:
                    sig["take_profit_price"] = float(c * (1 + tp_pct))
                    sig["stop_loss_price"] = float(c * (1 - sl_pct))
                elif position == -1:
                    sig["take_profit_price"] = float(c * (1 - tp_pct))
                    sig["stop_loss_price"] = float(c * (1 + sl_pct))
                    
                if year not in yearly_chunks:
                    yearly_chunks[year] = []
                yearly_chunks[year].append(sig)

    api_key = _load_api_key()
    
    for year in sorted(yearly_chunks.keys()):
        sigs = yearly_chunks[year]
        if len(sigs) == 0:
            continue
            
        # Sort signals by timestamp
        sigs = sorted(sigs, key=lambda x: x["ts"])
        
        # Hack to max out the $1M norm for portfolio
        if len(sigs) > 0:
            sigs[0]["strength"] = 100.0
            sigs[0]["notional"] = 950000.0
            
        payload = {
            "resolution": chosen_tf,
            "signals": sigs,
            "strategy": f"Chaos_Portfolio_{chosen_tf}_{year}",
            "start": f"{year}-01-01",
            "end": f"{year}-12-31"
        }

        print(f"Submitting {year} with {len(sigs)} multi-coin signals...")
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            out_file = ROOT / "Signal_Replay" / f"chaos_{year}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(out_file, "w") as f:
                json.dump({"response": data}, f, indent=2)
            print(f"Saved -> {out_file}")
        except Exception as e:
            print(f"Error submitting {year}: {e}")

if __name__ == "__main__":
    main()
