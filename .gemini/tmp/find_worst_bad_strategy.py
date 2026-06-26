
import json

file_path = '.gemini/skills/crypto-strategy-tuner/data/scan_results.json'

with open(file_path, 'r') as f:
    scan_results = json.load(f)

worst_bad_strategy = None
lowest_sharpe = float('inf')

for strategy in scan_results['results']:
    if strategy['grade'] == "BAD" and strategy['sharpe'] is not None and strategy['sharpe'] < lowest_sharpe:
        worst_bad_strategy = strategy
        lowest_sharpe = strategy['sharpe']

if worst_bad_strategy:
    print(json.dumps(worst_bad_strategy, indent=2))
else:
    print("No worst BAD strategy found.")
