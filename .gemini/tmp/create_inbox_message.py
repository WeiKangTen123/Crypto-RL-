
import datetime
import json
import os

ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
inbox_dir = '.gemini/skills/crypto-fullstack/inbox'
os.makedirs(inbox_dir, exist_ok=True)

message_content = {
    'strategy_id': '76',
    'class': 'MeanReversionFundingRateStrategy',
    'error_message': "DataFrame must contain a 'funding_rate' column for this strategy."
}

inbox_file_path = os.path.join(inbox_dir, f'{ts}_from_tuner_STRATEGY_ERROR_ESCALATION.json')

with open(inbox_file_path, 'w') as f:
    json.dump(message_content, f, indent=2)

print(f"Created inbox message: {inbox_file_path}")
