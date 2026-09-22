import sys

file_path = "strategy_backtest/settings.py"
with open(file_path, "r") as f:
    lines = f.readlines()

# find end of STRATEGY_LIBRARY by searching backwards from ACTIVE_STRATEGY
active_idx = -1
for i, line in enumerate(lines):
    if "ACTIVE_STRATEGY =" in line:
        active_idx = i
        break

if active_idx == -1:
    print("Could not find ACTIVE_STRATEGY.")
    sys.exit(1)

# Find the closing brace '}' before ACTIVE_STRATEGY
end_idx = -1
for i in range(active_idx - 1, -1, -1):
    if lines[i].strip() == "}":
        end_idx = i
        break

if end_idx == -1:
    print("Could not find STRATEGY_LIBRARY closing brace.")
    sys.exit(1)

entry = """    "179": {
        "id": "EMA_STREAK_1H",
        "desc": "EMA Streak 1H - Abacussa",
        "class": "EMAStreakStrategy",
        "data": {"coins": "BTC", "timeframes": "1h", "date_from": "2023-01-01", "date_to": "2026-05-31"},
        "risk": {"initial_balance": 1000, "risk_per_trade": 0.06, "leverage": 20,
                 "trading_fee": 0.0005, "maintenance_margin_rate": 0.005},
        "params": {
            "fast": 59, "slow": 261, "streakWin": 60, "momentumPct": 0.14, "useStreak": True,
            "stopLossPct": 0.02, "leverage_param": 20, "riskPerTrade": 0.06,
            "useTP": False, "takeProfitPct": 0.0, "safetyPinPct": 0.08, "safetyPinLockPct": 0.04
        },
    },
"""

lines.insert(end_idx, entry)

# Also update ACTIVE_STRATEGY
for i, line in enumerate(lines):
    if "ACTIVE_STRATEGY =" in line:
        lines[i] = 'ACTIVE_STRATEGY = "179"\n'
        break

with open(file_path, "w") as f:
    f.writelines(lines)

print("Added strategy 179 and updated ACTIVE_STRATEGY!")
