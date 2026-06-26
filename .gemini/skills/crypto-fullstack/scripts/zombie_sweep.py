import os
import json
import signal
import sys

"""
zombie_sweep.py — Checks active_watchers.json to ensure PIDs are alive.
If a watcher is dead but registered as alive, it clears the entry.
"""

WATCHER_FILE = "Crypto_Agent/active_watchers.json"

def sweep():
    if not os.path.exists(WATCHER_FILE):
        print("[INFO] No active_watchers.json found.")
        return

    with open(WATCHER_FILE, 'r') as f:
        try:
            watchers = json.load(f)
        except json.JSONDecodeError:
            print("[ERROR] Corrupt active_watchers.json. Resetting.")
            watchers = {}

    cleaned = {}
    changes = 0

    for agent_id, pid in watchers.items():
        try:
            # Signal 0 checks for process existence without killing it
            os.kill(pid, 0)
            cleaned[agent_id] = pid
        except OSError:
            print(f"[ZOMBIE] Agent {agent_id} (PID {pid}) is dead. Clearing entry.")
            changes += 1

    if changes > 0:
        with open(WATCHER_FILE, 'w') as f:
            json.dump(cleaned, f, indent=2)
        print(f"[RESULT] Sweep complete. Cleared {changes} zombie process(es).")
    else:
        print("[OK] All registered watchers are alive.")

if __name__ == "__main__":
    sweep()
