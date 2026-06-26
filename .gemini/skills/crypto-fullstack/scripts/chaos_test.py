import sys
import os
import time
import requests
from datetime import datetime

# Robust path insertion for shared logger
# Shared logger
sys.path.insert(0, '/Users/weikangten/Desktop/Crypto-RL/.gemini/shared')
from logger import log_to_agent

API_BASE = "http://127.0.0.1:5001"

ROUTES = [
    ("/", "GET"),
    ("/api/strategy_list", "GET"),
    ("/api/agent_console", "GET"),
    ("/agent_monitor", "GET"),
    ("/api/agent_telemetry", "GET"),
    ("/datasets", "GET"),
    ("/processed", "GET"),
    ("/data_preview?type=raw&coin=BTC&tf=4h", "GET"),
    ("/status", "GET"),
    ("/list_results", "GET"),
    ("/check_updates", "GET"),
]

POST_ROUTES = [
    ("/api/strategy_backtest", {"strategy_ids": ["1"], "date_from": "2023-01-01", "date_to": "2023-02-01"}),
    ("/api/agent_handshake", {"agent_id": "fullstack"}),
    ("/api/agent_offline", {"agent_id": "fullstack"}),
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}")
    log_to_agent('crypto-fullstack', msg)

def test_routes():
    log("Starting chaos test...")
    results = []
    
    for route, method in ROUTES:
        try:
            start = time.time()
            resp = requests.get(API_BASE + route, timeout=5)
            lat = time.time() - start
            log(f"[GET] {route:<30} | Status: {resp.status_code} | Latency: {lat:.3f}s")
            results.append({"route": route, "method": "GET", "status": resp.status_code, "latency": lat})
        except Exception as e:
            log(f"[GET] {route:<30} | FAILED: {e}")
            results.append({"route": route, "method": "GET", "status": "ERROR", "error": str(e)})

    for route, payload in POST_ROUTES:
        try:
            start = time.time()
            resp = requests.post(API_BASE + route, json=payload, timeout=10)
            lat = time.time() - start
            log(f"[POST] {route:<30} | Status: {resp.status_code} | Latency: {lat:.3f}s")
            results.append({"route": route, "method": "POST", "status": resp.status_code, "latency": lat})
        except Exception as e:
            log(f"[POST] {route:<30} | FAILED: {e}")
            results.append({"route": route, "method": "POST", "status": "ERROR", "error": str(e)})

    log(f"RESULT | chaos_test.py | Completed API sweep. {len([r for r in results if r['status'] == 200])}/{len(results)} routes OK.")

if __name__ == "__main__":
    test_routes()
