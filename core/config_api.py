'''
Binance API configuration.
Reads credentials from .env (BINANCE_API_KEY / BINANCE_API_SECRET).
Optional HTTPS_PROXY — set in .env if Binance is geo-blocked in your region.
'''

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_BINANCE    = os.getenv('BINANCE_API_KEY', '')
API_SECRET_BINANCE = os.getenv('BINANCE_API_SECRET', '')

# Proxy — None if not set or empty string
_proxy = os.getenv('HTTPS_PROXY', '').strip()
PROXIES = {'https': _proxy, 'http': _proxy} if _proxy else None
