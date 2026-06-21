"""Road-network routing. Prefers MapmyIndia / Mappls (official partner, India-grade),
falls back to public OSRM, then to straight-line geometry if both are unreachable."""
import numpy as np
import pandas as pd

from .config import MAPPLS_ROUTE_URL

OSRM = "https://router.project-osrm.org/route/v1/driving/"


def _haversine_km(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(np.radians, [a[0], a[1], b[0], b[1]])
    h = np.sin((la2-la1)/2)**2 + np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2
    return 2*R*np.arcsin(np.sqrt(h))


def _parse(d):
    g = pd.DataFrame(d["geometry"]["coordinates"], columns=["lon", "lat"])
    return g, round(d["distance"]/1000, 1), round(d["duration"]/60)


def road_route(coords, mappls_key=""):
    """coords: list of (lat, lon) in visiting order.
    Returns (geometry_df[lon,lat], distance_km, duration_min, provider)."""
    coords = [tuple(c) for c in coords]
    if len(coords) < 2:
        return pd.DataFrame(columns=["lon", "lat"]), 0.0, 0.0, "none"
    locs = ";".join(f"{lo},{la}" for la, lo in coords)
    try:
        import requests
        # 1) MapmyIndia / Mappls (preferred)
        if mappls_key:
            try:
                u = MAPPLS_ROUTE_URL.format(key=mappls_key, coords=locs)
                r = requests.get(u, timeout=12)
                if r.status_code == 200 and r.json().get("routes"):
                    g, km, mn = _parse(r.json()["routes"][0])
                    return g, km, mn, "MapmyIndia"
            except Exception:
                pass
        # 2) OSRM (OpenStreetMap)
        r = requests.get(OSRM + locs, params={"overview": "full", "geometries": "geojson"}, timeout=12)
        if r.status_code == 200 and r.json().get("routes"):
            g, km, mn = _parse(r.json()["routes"][0])
            return g, km, mn, "OSRM"
    except Exception:
        pass
    # 3) straight-line fallback
    g = pd.DataFrame(coords, columns=["lat", "lon"])[["lon", "lat"]]
    dist = sum(_haversine_km(coords[i], coords[i+1]) for i in range(len(coords)-1))
    return g, round(dist, 1), round(60*dist/18, 0), "straight-line"
