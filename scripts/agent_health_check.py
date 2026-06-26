import os
import json
import re

def check_file(path):
    if os.path.exists(path):
        return f"[PASS] Found: {path}"
    else:
        return f"[FAIL] Missing: {path}"

def check_heartbeat():
    path = 'main_controller/heartbeat.json'
    if not os.path.exists(path):
        return "[FAIL] Heartbeat file missing."
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        status = data.get('status', 'N/A')
        action = data.get('action', 'N/A')
        if re.search(r'\[\d+/\d+\]', action):
            return f"[PASS] Heartbeat evolution active: {status} | {action}"
        else:
            return f"[WARN] Heartbeat active but missing [X/Y] prefix: {action}"
    except Exception as e:
        return f"[ERROR] Heartbeat check failed: {e}"

def check_factor_library():
    # Check for recent cards
    lib_path = 'factor_library'
    recent_found = False
    for root, dirs, files in os.walk(lib_path):
        for file in files:
            if file.endswith('.md') and '20260610' in file:
                recent_found = True
                # Check for hypothesis structure
                with open(os.path.join(root, file), 'r') as f:
                    content = f.read()
                    if '## Concept' in content and '## Math/Logic' in content:
                        return f"[PASS] Factor Library updated with Hypothesis structure: {file}"
    return "[FAIL] No recent (2026-06-10) factor cards found with correct structure."

def check_library_dry():
    path = 'strategy_backtest/library.py'
    if not os.path.exists(path):
        return "[FAIL] library.py missing."
    with open(path, 'r') as f:
        content = f.read()
        if 'def calc_' in content or 'def detect_' in content:
            return "[PASS] library.py contains modular factor functions."
    return "[WARN] library.py found but appears empty of functions."

def main():
    print("=== FULL SYSTEM AGENT VALIDATION ===")
    print(f"Project: Crypto-RL")
    print(f"Agent: @alpha-researcher & @alpha-developer")
    print("-" * 40)
    
    print(check_heartbeat())
    print(check_factor_library())
    print(check_library_dry())
    print(check_file('main_controller/activity.log'))
    print(check_file('.gemini/skills/alpha-researcher/SKILL.md'))
    print(check_file('.gemini/skills/alpha-developer/SKILL.md'))
    
    # Check if FACTOR_ENG (Developer Stage 3) logic is visible in strategies
    strategies_dir = 'strategy_backtest/strategies'
    imported_count = 0
    total_count = 0
    for file in os.listdir(strategies_dir):
        if file.endswith('.py') and file != '__init__.py':
            total_count += 1
            with open(os.path.join(strategies_dir, file), 'r') as f:
                if 'from strategy_backtest.library import' in f.read():
                    imported_count += 1
    
    if total_count > 0:
        print(f"[INFO] FACTOR_ENG Check: {imported_count}/{total_count} strategies use library.py")
    
    print("-" * 40)
    print("Testing Complete.")

if __name__ == "__main__":
    main()
