import sys

file_path = "strategy_backtest/settings.py"
with open(file_path, "r") as f:
    lines = f.readlines()

end_idx = -1
for i, line in enumerate(lines):
    if line.startswith("}") and lines[i-1].strip() == "},":
        end_idx = i
        break
    if line.strip() == "}":
        # Let's find the closing brace before ACTIVE_STRATEGY
        if i + 2 < len(lines) and "ACTIVE_STRATEGY" in lines[i+2]:
            end_idx = i
            break

if end_idx == -1:
    print("Could not find STRATEGY_LIBRARY closing brace.")
    sys.exit(1)

coins = ["BTC", "ETH", "SOL", "XRP"]
tfs = ["5m", "15m", "1h", "4h", "1d"]

new_entries = []
strat_id = 159

for coin in coins:
    for tf in tfs:
        entry = f"""    "{strat_id}": {{
        "id": "FORGE_EMA_MACD_{coin}_{tf.upper()}",
        "desc": "EMA MACD Cross ({coin}, {tf})",
        "class": "ForgeStrategy",
        "data": {{"coins": "{coin}", "timeframes": "{tf}", "date_from": "2023-01-01", "date_to": "2026-06-01"}},
        "risk": {{"initial_balance": 1000, "risk_per_trade": 0.1, "leverage": 10,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005}},
        "params": {{
            "entry": "ema_macd_cross",
            "filters": [],
            "exit_method": "atr_tp_sl",
            "ema_fast": 5,
            "ema_slow": 20,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "tp_atr_mult": 2.0,
            "sl_atr_mult": 1.0,
            "atr_period": 14
        }},
    }},
"""
        new_entries.append(entry)
        strat_id += 1

lines.insert(end_idx, "".join(new_entries))

with open(file_path, "w") as f:
    f.writelines(lines)

print("Added 20 strategies!")
