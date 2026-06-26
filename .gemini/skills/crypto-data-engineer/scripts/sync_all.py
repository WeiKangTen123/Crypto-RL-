"""
sync_all.py — one-command data sync for all 5 coins.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR    = os.path.dirname(SCRIPT_DIR)
ROOT_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(AGENT_DIR)))
VENV_PYTHON  = os.path.join(ROOT_DIR, 'venv', 'bin', 'python')

# Shared logger
sys.path.insert(0, '/Users/weikangten/Desktop/Crypto-RL/.gemini/shared')
from logger import log_to_agent
from memory_manager import update_session_memory

FETCHER_OHLCV    = os.path.join(SCRIPT_DIR, 'incremental_fetcher.py')
FETCHER_FUNDING  = os.path.join(SCRIPT_DIR, 'funding_rate_fetcher.py')
VPN_MANAGER      = os.path.join(SCRIPT_DIR, 'vpn_manager.py')

COINS    = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
FUNDING_TF = '4h'


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}")
    log_to_agent('crypto-data-engineer', msg)


def run(cmd: list, label: str) -> bool:
    log(f'  → {label}')
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    ok = result.returncode == 0
    log(f'  {"✓" if ok else "✗"} {label} — {"OK" if ok else f"exit {result.returncode}"}')
    return ok


def vpn_connect() -> bool:
    log('[VPN] Connecting...')
    result = subprocess.run([VENV_PYTHON, VPN_MANAGER, 'connect'], cwd=ROOT_DIR)
    return result.returncode == 0


def vpn_disconnect():
    log('[VPN] Disconnecting...')
    subprocess.run([VENV_PYTHON, VPN_MANAGER, 'disconnect'], cwd=ROOT_DIR)


def sync_ohlcv() -> bool:
    log('[OHLCV] Starting incremental fetch for all coins/timeframes...')
    ok = run(
        [VENV_PYTHON, FETCHER_OHLCV],
        'incremental_fetcher.py — all coins × all timeframes'
    )
    return ok


def sync_funding() -> bool:
    log('[FUNDING] Starting incremental fetch for all coins @ 4h...')
    ok = run(
        [VENV_PYTHON, FETCHER_FUNDING,
         '--coins', *COINS,
         '--timeframes', FUNDING_TF,
         '--incremental'],
        f'funding_rate_fetcher.py --incremental — {", ".join(COINS)} @ {FUNDING_TF}'
    )
    return ok


def main():
    parser = argparse.ArgumentParser(description='Sync all datasets to latest')
    parser.add_argument('--ohlcv-only',   action='store_true', help='Only sync OHLCV, skip funding rate')
    parser.add_argument('--funding-only', action='store_true', help='Only sync funding rate, skip OHLCV')
    parser.add_argument('--no-vpn',       action='store_true', help='Skip VPN connect/disconnect (use if VPN already active)')
    args = parser.parse_args()

    log('=== SYNC ALL START ===')
    results = {}
    vpn_was_connected = False

    # ── Step 1: VPN ──────────────────────────────────────────────────────────
    if not args.no_vpn:
        vpn_was_connected = vpn_connect()
        if not vpn_was_connected:
            log('[ERROR] VPN failed to connect — aborting sync. Run vpn_manager.py status to diagnose.')
            log('=== SYNC ALL ABORTED ===')
            sys.exit(1)
    else:
        log('[VPN] Skipped (--no-vpn flag set)')

    try:
        # ── Step 2: OHLCV ────────────────────────────────────────────────────
        if not args.funding_only:
            results['ohlcv'] = sync_ohlcv()
        else:
            log('[OHLCV] Skipped (--funding-only flag set)')

        # ── Step 3: Funding rate ─────────────────────────────────────────────
        if not args.ohlcv_only:
            results['funding'] = sync_funding()
        else:
            log('[FUNDING] Skipped (--ohlcv-only flag set)')

    finally:
        # ── Step 4: VPN disconnect — always runs even if fetch fails ─────────
        if not args.no_vpn and vpn_was_connected:
            vpn_disconnect()

    # ── Summary ───────────────────────────────────────────────────────────────
    log('')
    log('=== SYNC ALL COMPLETE ===')
    for key, ok in results.items():
        log(f'  {key.upper():<10} {"✓ OK" if ok else "✗ FAILED"}')

    if any(not ok for ok in results.values()):
        sys.exit(1)

    # Update session memory
    update_session_memory(
        'crypto-data-engineer',
        f'Data sync completed: {", ".join([k.upper() for k, ok in results.items() if ok])}',
        'dataset/',
        comms='None',
        open_items='None',
        outcome='COMPLETE' if all(results.values()) else 'ISSUES_FOUND',
        duration=0 # Sync time not tracked
    )


if __name__ == '__main__':
    main()
