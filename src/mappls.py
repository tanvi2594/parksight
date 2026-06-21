"""MapmyIndia / Mappls OAuth helper.

Mappls REST APIs (map tiles, routing, geocoding) authenticate with a short-lived
**access token** obtained from a client_id + client_secret (OAuth client-credentials),
NOT a lone static key. This module fetches and caches that token so the rest of the
app can use Mappls; if credentials are missing/invalid it returns None and the app
falls back to free OpenStreetMap / OSRM (so no credit is ever wasted on bad calls)."""
import time

_TOKEN_URL = "https://outpost.mappls.com/api/security/oauth/token"
_cache = {}            # (cid, secret) -> (token, expiry_epoch)


def get_token(client_id: str, client_secret: str):
    """Return a cached Mappls access token, or None if creds are missing/invalid.
    Cached for the token's lifetime so we spend at most ~1 auth call per hour."""
    if not client_id or not client_secret:
        return None
    key = (client_id, client_secret)
    now = time.time()
    if key in _cache and _cache[key][1] > now:
        return _cache[key][0]
    try:
        import requests
        r = requests.post(_TOKEN_URL, data={"grant_type": "client_credentials",
                                            "client_id": client_id,
                                            "client_secret": client_secret}, timeout=12)
        if r.status_code == 200:
            j = r.json()
            tok = j.get("access_token")
            if tok:
                _cache[key] = (tok, now + int(j.get("expires_in", 3600)) - 60)
                return tok
    except Exception:
        pass
    return None
