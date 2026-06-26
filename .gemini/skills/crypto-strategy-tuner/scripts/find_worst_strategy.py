import json

def find_worst_bad_strategy(scan_results_path):
    with open(scan_results_path, 'r') as f:
        data = json.load(f)

    worst_strategy = None
    lowest_sharpe = float('inf')

    for strategy in data['results']:
        if strategy['grade'] == 'BAD':
            # Handle cases where sharpe might be missing or null for BAD strategies
            sharpe = strategy.get('sharpe')
            if sharpe is None:
                # Assign a very low value if sharpe is null or missing for BAD strategies
                sharpe = -float('inf') 
            
            if sharpe < lowest_sharpe:
                lowest_sharpe = sharpe
                worst_strategy = strategy
    return worst_strategy

if __name__ == "__main__":
    scan_results_file = '.gemini/skills/crypto-strategy-tuner/data/scan_results.json'
    worst_bad = find_worst_bad_strategy(scan_results_file)

    if worst_bad:
        print(f"Worst BAD strategy ID: {worst_bad['id']}")
        print(f"Class: {worst_bad['class']}")
        print(f"Sharpe: {worst_bad['sharpe']}")
        print(f"Reason: {worst_bad['grade_reason']}")
    else:
        print("No BAD strategies found or an error occurred.")
