"""
vpn_manager.py — ProtonVPN connect/disconnect/status helper for the data engineer agent.

Uses macOS AppleScript UI automation to click ProtonVPN's Quick Connect / Disconnect buttons.
Requires Terminal to have Accessibility access:
  System Settings → Privacy & Security → Accessibility → Terminal → ON

Usage:
    python .gemini/skills/crypto-data-engineer/scripts/vpn_manager.py connect
    python .gemini/skills/crypto-data-engineer/scripts/vpn_manager.py disconnect
    python .gemini/skills/crypto-data-engineer/scripts/vpn_manager.py status
"""

import sys
import time
import subprocess
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
    '.env'
))

BINANCE_TEST_URL = 'https://fapi.binance.com/fapi/v1/ping'
CONNECT_WAIT_SECS = 40
CHECK_INTERVAL    = 3


def _run_applescript(script: str) -> str:
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip()


def _get_button_names() -> list:
    script = '''
tell application "System Events"
    tell process "ProtonVPN"
        get name of every button of window 1
    end tell
end tell'''
    out = _run_applescript(script)
    return [b.strip() for b in out.split(',') if b.strip() and b.strip() != 'missing value']


def _click_button(button_name: str) -> bool:
    script = f'''
tell application "System Events"
    tell process "ProtonVPN"
        click button "{button_name}" of window 1
    end tell
end tell'''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.returncode == 0


def is_binance_reachable(timeout: int = 6) -> bool:
    proxy = os.getenv('HTTPS_PROXY', '').strip()
    proxies = {'https': proxy, 'http': proxy} if proxy else None
    try:
        r = requests.get(BINANCE_TEST_URL, timeout=timeout, proxies=proxies)
        return r.status_code == 200
    except Exception:
        return False


def is_vpn_connected() -> bool:
    """Check ProtonVPN UI state — Disconnect button = connected."""
    try:
        # Launch ProtonVPN if not running
        subprocess.run(['open', '-a', 'ProtonVPN'], capture_output=True)
        time.sleep(1)
        buttons = _get_button_names()
        return 'Disconnect' in buttons
    except Exception:
        return False


def connect(wait: int = CONNECT_WAIT_SECS) -> bool:
    print('[VPN] Checking current state...')

    # Already connected?
    if is_vpn_connected():
        print('[VPN] Already connected.')
        if is_binance_reachable():
            print('[VPN] Binance reachable ✓')
            return True

    # Open ProtonVPN and wait for UI to load
    subprocess.run(['open', '-a', 'ProtonVPN'], capture_output=True)
    time.sleep(3)

    buttons = _get_button_names()
    print(f'[VPN] Buttons visible: {buttons}')

    if 'Quick Connect' in buttons:
        print('[VPN] Clicking Quick Connect...')
        _click_button('Quick Connect')
    elif 'Connect' in buttons:
        print('[VPN] Clicking Connect...')
        _click_button('Connect')
    else:
        print(f'[VPN] ERROR: No connect button found. Buttons: {buttons}')
        return False

    print(f'[VPN] Waiting up to {wait}s for connection...')
    elapsed = 0
    while elapsed < wait:
        time.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL
        if is_binance_reachable():
            print(f'[VPN] Connected — Binance reachable after {elapsed}s ✓')
            return True
        print(f'[VPN] Still connecting... ({elapsed}s)')

    print('[VPN] ERROR: Timed out waiting for VPN connection.')
    return False


def disconnect() -> bool:
    print('[VPN] Disconnecting...')
    subprocess.run(['open', '-a', 'ProtonVPN'], capture_output=True)
    time.sleep(1)
    buttons = _get_button_names()

    if 'Disconnect' in buttons:
        _click_button('Disconnect')
        time.sleep(2)
        print('[VPN] Disconnected ✓')
        return True
    else:
        print(f'[VPN] Not connected (buttons: {buttons})')
        return True


def status() -> str:
    connected = is_vpn_connected()
    reachable = is_binance_reachable() if connected else False
    state = 'CONNECTED' if connected else 'DISCONNECTED'
    binance = 'reachable' if reachable else 'not reachable'
    print(f'[VPN] Status: {state} | Binance: {binance}')
    return state


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'connect':
        ok = connect()
        sys.exit(0 if ok else 1)
    elif cmd == 'disconnect':
        ok = disconnect()
        sys.exit(0 if ok else 1)
    elif cmd == 'status':
        status()
    else:
        print(f'Usage: vpn_manager.py [connect|disconnect|status]')
        sys.exit(1)
