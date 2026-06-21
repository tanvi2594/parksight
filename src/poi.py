"""Points-of-interest context (OpenStreetMap / Overpass): do illegal-parking hotspots
cluster around commercial areas, markets and metro stations — as the theme states?"""
import json
import numpy as np
import pandas as pd

from .config import OUT, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX

_BBOX = f"{LAT_MIN},{LON_MIN},{LAT_MAX},{LON_MAX}"
_QUERY = f"""
[out:json][timeout:90];
(
  nwr["station"="subway"]({_BBOX});
  nwr["railway"="station"]["subway"="yes"]({_BBOX});
  nwr["amenity"="marketplace"]({_BBOX});
  nwr["shop"="mall"]({_BBOX});
  nwr["amenity"="bus_station"]({_BBOX});
);
out center;
"""
_ENDPOINTS = ["https://overpass-api.de/api/interpreter",
              "https://overpass.kumi.systems/api/interpreter"]


def _kind(tags):
    if tags.get("station") == "subway" or tags.get("subway") == "yes":
        return "Metro"
    if tags.get("amenity") == "marketplace":
        return "Market"
    if tags.get("shop") == "mall":
        return "Mall"
    if tags.get("amenity") == "bus_station":
        return "Bus station"
    return "Other"


def fetch_poi(force=False) -> pd.DataFrame:
    cache = OUT / "poi.csv"
    if cache.exists() and not force:
        return pd.read_csv(cache)
    rows = []
    try:
        import requests
        for url in _ENDPOINTS:
            try:
                r = requests.post(url, data={"data": _QUERY}, timeout=90)
                if r.status_code == 200:
                    for el in r.json().get("elements", []):
                        lat = el.get("lat") or el.get("center", {}).get("lat")
                        lon = el.get("lon") or el.get("center", {}).get("lon")
                        if lat and lon:
                            rows.append({"lat": lat, "lon": lon,
                                         "kind": _kind(el.get("tags", {})),
                                         "name": el.get("tags", {}).get("name", "")})
                    break
            except Exception:
                continue
    except Exception:
        pass
    poi = pd.DataFrame(rows)
    if len(poi):
        poi = poi[poi.kind != "Other"].drop_duplicates(["lat", "lon"]).reset_index(drop=True)
        poi.to_csv(cache, index=False)
    return poi


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1); dl = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))


def context_stats(zones: pd.DataFrame, poi: pd.DataFrame, top_n=50, radius_m=400):
    """For the top-N hotspot zones: nearest POI distance + share within `radius_m`."""
    if poi is None or not len(poi):
        return {"available": False}, zones.assign(near_poi=None, near_m=None)
    z = zones.head(top_n).copy()
    plat, plon = poi.lat.values, poi.lon.values
    near_kind, near_m = [], []
    for r in z.itertuples():
        d = _haversine_m(r.lat, r.lon, plat, plon)
        i = int(np.argmin(d)); near_kind.append(poi.kind.values[i]); near_m.append(float(d[i]))
    z["near_poi"] = near_kind; z["near_m"] = np.round(near_m, 0)
    within = z.near_m <= radius_m
    stats = {
        "available": True,
        "n_poi": int(len(poi)),
        "poi_breakdown": poi.kind.value_counts().to_dict(),
        "top_n": top_n, "radius_m": radius_m,
        "pct_top_near_poi": round(100 * within.mean(), 1),
        "pct_near_metro": round(100 * (z.near_poi.eq("Metro") & within).mean(), 1),
        "pct_near_market_mall": round(100 * (z.near_poi.isin(["Market", "Mall"]) & within).mean(), 1),
    }
    return stats, z[["zone_rank", "name", "CIS_100", "near_poi", "near_m", "police_station"]]
