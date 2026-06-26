import json
from datetime import datetime, timedelta

def check_finetune_status(finetune_results_path, strategy_id, grace_period_hours=24):
    try:
        with open(finetune_results_path, 'r') as f:
            finetune_results = json.load(f)
    except FileNotFoundError:
        return False, "finetune_results.json not found."
    except json.JSONDecodeError:
        return False, "Error decoding finetune_results.json."

    for result in finetune_results:
        if result.get('strategy_id') == strategy_id:
            finetuned_at_str = result.get('finetuned_at')
            if finetuned_at_str:
                finetuned_at = datetime.fromisoformat(finetuned_at_str)
                # Current time as per the prompt's context
                # Assuming current time is fixed to Friday, June 12, 2026, 12:00:00 (midday for simplicity)
                # In a real scenario, datetime.now() would be used, but for consistent execution here,
                # I'm using the provided context.
                # For safety and to simulate "now", I'll use the current time when this script runs.
                current_time = datetime.now() # Use actual current time for robust check

                if (current_time - finetuned_at) < timedelta(hours=grace_period_hours):
                    return True, f"Strategy ID {strategy_id} was fine-tuned within the last {grace_period_hours} hours."
    return False, f"Strategy ID {strategy_id} not found in finetune results or not fine-tuned recently."

if __name__ == "__main__":
    finetune_results_file = '.gemini/skills/crypto-strategy-tuner/data/finetune_results.json'
    strategy_to_check = "66" # The worst BAD strategy ID

    is_recent, message = check_finetune_status(finetune_results_file, strategy_to_check)
    print(message)
    if is_recent:
        print("ACTION: SKIP_FINETUNE")
    else:
        print("ACTION: PROCEED_FINETUNE")
