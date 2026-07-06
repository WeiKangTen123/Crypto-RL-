import json
from datetime import datetime, timedelta

def find_eligible():
    now = datetime.now()
    cutoff = now - timedelta(hours=24)

    with open('.gemini/skills/crypto-strategy-tuner/data/scan_results.json', 'r') as f:
        scan_data = json.load(f)
    try:
        with open('.gemini/skills/crypto-strategy-tuner/data/finetune_results.json', 'r') as f:
            finetune_data = json.load(f)
    except FileNotFoundError:
        finetune_data = []

    # Map strategy_id -> latest finetuned datetime
    finetune_map = {}
    for item in finetune_data:
        sid = item.get('strategy_id')
        ft_at_str = item.get('finetuned_at')
        if sid and ft_at_str:
            try:
                # remove timezone offset if any
                clean_time = ft_at_str.split('+')[0].split('Z')[0]
                dt = datetime.fromisoformat(clean_time)
                if sid not in finetune_map or dt > finetune_map[sid]:
                    finetune_map[sid] = dt
            except Exception as e:
                print(f"Error parsing date {ft_at_str}: {e}")

    print(f"Current local time: {now}")
    print(f"Cutoff time (24h ago): {cutoff}")
    print("Recently tuned strategies:")
    for sid, dt in sorted(finetune_map.items()):
        if dt >= cutoff:
            print(f"  ID {sid}: tuned at {dt}")

    # List all BAD strategies and sort by Sharpe
    bad_strategies = []
    for item in scan_data.get('results', []):
        if item.get('grade') == 'BAD':
            sid = item.get('id')
            class_name = item.get('class')
            sharpe = item.get('sharpe')
            if sharpe is None:
                sharpe = -999.0
            
            last_tuned = finetune_map.get(sid)
            is_eligible = True
            if last_tuned and last_tuned >= cutoff:
                is_eligible = False
            
            bad_strategies.append({
                'id': sid,
                'class': class_name,
                'sharpe': sharpe,
                'last_tuned': last_tuned,
                'is_eligible': is_eligible,
                'reason': item.get('grade_reason', '')
            })

    # Sort by Sharpe (lowest first)
    bad_strategies.sort(key=lambda x: x['sharpe'])

    print("\nWorst BAD strategies sorted by Sharpe:")
    found_eligible = False
    for i, s in enumerate(bad_strategies[:15]):
        status = "ELIGIBLE" if s['is_eligible'] else "TUNED_RECENTLY"
        tuned_str = s['last_tuned'].isoformat() if s['last_tuned'] else "Never"
        print(f"{i+1}. ID: {s['id']}, Class: {s['class']}, Sharpe: {s['sharpe']:.2f}, Last Tuned: {tuned_str}, Status: {status}")
        if s['is_eligible'] and not found_eligible:
            print(f"   => NEXT TARGET FOR TUNING: ID {s['id']} ({s['class']})")
            found_eligible = True

if __name__ == '__main__':
    find_eligible()
