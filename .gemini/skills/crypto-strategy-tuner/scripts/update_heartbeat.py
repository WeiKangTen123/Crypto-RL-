import json
import sys
from datetime import datetime

def update_heartbeats(action_text):
    now_iso = datetime.utcnow().isoformat()
    now_utc_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + " UTC"
    model_name = "gemini-3.5-flash"

    # 1. Update local skill heartbeat
    local_path = ".gemini/skills/crypto-strategy-tuner/heartbeat.json"
    try:
        with open(local_path, "w") as f:
            json.dump({
                "ts": now_iso,
                "status": "ONLINE",
                "action": action_text,
                "last_action": action_text,
                "model": model_name
            }, f, indent=2)
        print(f"Updated {local_path}")
    except Exception as e:
        print(f"Error updating {local_path}: {e}")

    # 2. Update root heartbeat
    root_path = "heartbeat.json"
    try:
        with open(root_path, "w") as f:
            json.dump({
                "status": "ONLINE",
                "action": action_text
            }, f, indent=2)
        print(f"Updated {root_path}")
    except Exception as e:
        print(f"Error updating {root_path}: {e}")

    # 3. Update shared heartbeat
    shared_path = ".gemini/shared/heartbeat.json"
    try:
        with open(shared_path, "r") as f:
            shared_data = json.load(f)
    except Exception:
        shared_data = {}

    shared_data["crypto-strategy-tuner"] = {
        "status": "ONLINE",
        "action": action_text,
        "last_updated": now_utc_str
    }
    shared_data["ts"] = now_iso
    shared_data["status"] = "ONLINE"
    shared_data["action"] = action_text
    shared_data["last_action"] = action_text

    try:
        with open(shared_path, "w") as f:
            json.dump(shared_data, f, indent=2)
        print(f"Updated {shared_path}")
    except Exception as e:
        print(f"Error updating {shared_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_heartbeat.py <action_text>")
        sys.exit(1)
    update_heartbeats(sys.argv[1])
