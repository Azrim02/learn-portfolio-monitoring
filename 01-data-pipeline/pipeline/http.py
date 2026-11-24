"""One polite HTTP helper for all sources."""
import time

import requests


def get(url, *, params=None, headers=None, pause=1.0):
    time.sleep(pause)   # FRED asks clients to wait 1 second between requests
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text
