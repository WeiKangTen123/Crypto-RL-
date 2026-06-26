
import json
import datetime

file_path = '.gemini/skills/crypto-strategy-tuner/data/scan_results.json'

with open(file_path, 'r') as f:
    scan_results = json.load(f)

good_count = 0
mediocre_count = 0
bad_count = 0
error_count = 0

updated_results = []
for strategy in scan_results['results']:
    grade = ""
    grade_reason = ""

    if strategy.get('error') is not None:
        grade = "ERROR"
        grade_reason = strategy['error']
        error_count += 1
    elif strategy.get('sharpe') is None or strategy.get('total_trades', 0) < 10:
        grade = "BAD"
        grade_reason = "Too few trades for reliable statistical conclusions or missing Sharpe ratio."
        bad_count += 1
    else:
        sharpe = strategy['sharpe']
        total_return = strategy.get('total_return', 0)
        profit_factor = strategy.get('profit_factor', 0)
        max_drawdown = strategy.get('max_drawdown', 0)

        if sharpe >= 1.0:
            grade = "GOOD"
            grade_reason = "Excellent risk-adjusted returns."
            good_count += 1
        elif 0.3 <= sharpe < 1.0:
            grade = "MEDIOCRE"
            grade_reason = "Acceptable risk-adjusted returns, but could be improved."
            mediocre_count += 1
        else: # sharpe < 0.3
            grade = "BAD"
            if total_return < 0:
                grade_reason = "Strategy loses money overall."
            elif profit_factor < 1.0:
                grade_reason = "Profit factor less than 1.0 indicates a losing strategy per trade."
            elif max_drawdown > 50.0: # Arbitrary high drawdown threshold
                grade_reason = "High drawdown makes it unsuitable."
            else:
                grade_reason = "Poor risk-adjusted returns."
            bad_count += 1
            
    strategy['grade'] = grade
    strategy['grade_reason'] = grade_reason
    updated_results.append(strategy)

scan_results['results'] = updated_results
scan_results['classified'] = True
scan_results['GOOD'] = good_count
scan_results['MEDIOCRE'] = mediocre_count
scan_results['BAD'] = bad_count
scan_results['ERROR'] = error_count

scan_results['scanned_at'] = datetime.datetime.now().isoformat()

with open(file_path, 'w') as f:
    json.dump(scan_results, f, indent=2)

print(f"Updated scan_results.json with grades. GOOD: {good_count}, MEDIOCRE: {mediocre_count}, BAD: {bad_count}, ERROR: {error_count}")
