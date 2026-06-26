
import datetime
import json

# Get current timestamp
timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

# Log to activity.log
with open('.gemini/skills/crypto-strategy-tuner/activity.log', 'a') as f:
    f.write('[' + timestamp + '] INFO | Classified scan_results.json. GOOD: 0, MEDIOCRE: 24, BAD: 45, ERROR: 1
')

# Log to SYSTEM_CHANGELOG.md
with open('.gemini/shared/SYSTEM_CHANGELOG.md', 'a') as f:
    f.write('| ' + timestamp + ' | @crypto-strategy-tuner | .gemini/skills/crypto-strategy-tuner/data/scan_results.json | Updated strategy grades and counts | Classified scan results based on Sharpe ratio criteria.
')

# Log to AGENT_COLLABORATION.md
# We need to read scan_results.json to get the total number of strategies
file_path = '.gemini/skills/crypto-strategy-tuner/data/scan_results.json'
with open(file_path, 'r') as f:
    scan_results = json.load(f)

total_strategies = scan_results['total']
good_count = scan_results['GOOD']
mediocre_count = scan_results['MEDIOCRE']
bad_count = scan_results['BAD']
error_count = scan_results['ERROR']

with open('.gemini/shared/AGENT_COLLABORATION.md', 'a') as f:
    f.write('| ' + timestamp + ' | @crypto-strategy-tuner | Classified ' + str(total_strategies) + ' strategies. GOOD: ' + str(good_count) + ', MEDIOCRE: ' + str(mediocre_count) + ', BAD: ' + str(bad_count) + ', ERROR: ' + str(error_count) + ' | Scan completed.
')

print("All log files updated successfully.")
