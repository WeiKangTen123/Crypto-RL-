import pandas as pd
import json
import os

# Window definitions: (duration_months, step_months, category, trials)
# trials = Optuna trials to use per window — shorter windows get fewer trials
WINDOW_SPECS = [
    # MICRO
    {"type": "1M",  "category": "MICRO",  "duration_months": 1,  "step_months": 1,  "trials": 15},
    {"type": "2M",  "category": "MICRO",  "duration_months": 2,  "step_months": 1,  "trials": 15},
    # MESO
    {"type": "3M",  "category": "MESO",   "duration_months": 3,  "step_months": 1,  "trials": 25},
    {"type": "4M",  "category": "MESO",   "duration_months": 4,  "step_months": 2,  "trials": 25},
    {"type": "6M",  "category": "MESO",   "duration_months": 6,  "step_months": 2,  "trials": 25},
    # MACRO — use years as months for simplicity
    {"type": "1Y",  "category": "MACRO",  "duration_months": 12, "step_months": 6,  "trials": 40},
    {"type": "2Y",  "category": "MACRO",  "duration_months": 24, "step_months": 12, "trials": 40},
    {"type": "3Y",  "category": "MACRO",  "duration_months": 36, "step_months": 36, "trials": 40},
]


def generate_windows(start_date="2023-01-01", end_date=None):
    # Default: end of last complete month so we never include partial windows
    if end_date is None:
        today    = pd.Timestamp.today()
        end_date = (today.replace(day=1) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    start = pd.to_datetime(start_date)
    end   = pd.to_datetime(end_date)
    windows = []

    for spec in WINDOW_SPECS:
        cur = start
        while True:
            w_end = cur + pd.DateOffset(months=spec["duration_months"]) - pd.Timedelta(days=1)
            if w_end > end:
                break
            windows.append({
                "type":     spec["type"],
                "category": spec["category"],
                "trials":   spec["trials"],
                "start":    cur.strftime('%Y-%m-%d'),
                "end":      w_end.strftime('%Y-%m-%d'),
            })
            cur += pd.DateOffset(months=spec["step_months"])

    return windows


if __name__ == "__main__":
    win_list = generate_windows()

    by_type = {}
    for w in win_list:
        by_type.setdefault(w['type'], []).append(w)

    print(f"Generated {len(win_list)} total windows:")
    for spec in WINDOW_SPECS:
        t = spec['type']
        ws = by_type.get(t, [])
        if ws:
            print(f"  {spec['category']:5s}  {t:3s}  ({len(ws):3d} windows)  "
                  f"{ws[0]['start']} → {ws[0]['end']}  ...  {ws[-1]['start']} → {ws[-1]['end']}  "
                  f"[{spec['trials']} trials]")

    output_path = "phase_7/data/generated_windows.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(win_list, f, indent=4)
    print(f"\nSaved {len(win_list)} windows to {output_path}")
