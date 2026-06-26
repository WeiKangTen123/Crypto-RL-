import subprocess
import os

windows = [
    ("2023-01-01", "2023-06-30"),
    ("2024-01-01", "2024-06-30"),
    ("2025-01-01", "2025-06-30"),
    ("2026-01-01", "2026-05-01"),
]

strategy_id = "30"

print(f"Starting WFO for strategy {strategy_id}...")

for i, (start, end) in enumerate(windows):
    print(f"\n--- Window {i+1}: {start} to {end} ---")
    cmd = [
        "./venv/bin/python", "strategy_backtest/run_backtest.py",
        "--strategy", strategy_id,
        "--date_from", start,
        "--date_to", end
    ]
    subprocess.run(cmd)
