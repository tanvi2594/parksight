"""Aggregate violations into H3 cells, compute the Congestion-Impact Score (CIS),
classify chronic vs sporadic, and cluster cells into named enforcement zones."""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from .config import OUT
from .pipeline import cell_to_latlng


def _area_name(loc):
    if not isinstance(loc, str):
        return None
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    # prefer a locality-looking token (2nd component is usually the area/block)
    for p in parts[1:3]:
        if not any(ch.isdigit() for ch in p) and len(p) > 2:
            return p
    return parts[0] if parts else None


def _mode(s):
    s = s.dropna()
    return s.mode().iloc[0] if len(s) else None


def cell_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per H3 cell with congestion-impact metrics."""
    total_days = df.date.nunique()
    df = df.copy()
    df["area"] = df.location.map(_area_name)

    g = df.groupby("h3")
    cells = g.agg(
        n_total=("id", "size"),
        n_parking=("is_parking", "sum"),
        severity_mean=("severity", "mean"),
        severity_sum=("severity", "sum"),
        n_days=("date", "nunique"),
        peak_share=("is_peak", "mean"),
        weekend_share=("is_weekend", "mean"),
    ).reset_index()

    cells["persistence"] = cells.n_days / total_days
    cells["top_violation"] = g["top_violation"].apply(_mode).values
    cells["area"] = g["area"].apply(_mode).values
    cells["junction"] = g["junction_name"].apply(lambda s: _mode(s[s != "No Junction"]) or "No Junction").values
    cells["police_station"] = g["police_station"].apply(_mode).values
    cells["top_vehicle"] = g["vehicle_type"].apply(_mode).values

    cc = cells.h3.map(cell_to_latlng)
    cells["lat"] = [c[0] for c in cc]
    cells["lon"] = [c[1] for c in cc]

    # ---- Congestion-Impact Score -------------------------------------------
    # impact = parking volume x mean severity x chronicity x peak-overlap
    raw = (cells.n_parking
           * cells.severity_mean
           * (0.4 + 0.6 * cells.persistence)
           * (0.6 + 0.4 * cells.peak_share))
    cells["cis_raw"] = raw
    cells["CIS"] = (100 * np.log1p(raw) / np.log1p(raw.max())).round(2)

    # ---- chronicity class --------------------------------------------------
    def cls(p, n):
        if n >= 20 and p >= 0.5:
            return "Chronic"
        if n >= 8 and p >= 0.2:
            return "Recurring"
        return "Sporadic"
    cells["class"] = [cls(p, n) for p, n in zip(cells.persistence, cells.n_total)]
    cells["rank"] = cells.CIS.rank(ascending=False, method="first").astype(int)
    cells = cells.sort_values("CIS", ascending=False).reset_index(drop=True)
    cells["total_days"] = total_days
    return cells


def cluster_zones(cells: pd.DataFrame, top_frac=0.15, eps_m=350, min_samples=2) -> pd.DataFrame:
    """Merge the highest-impact adjacent cells into enforcement ZONES via DBSCAN
    (haversine on cell centres). min_samples=2 -> a zone must be a genuine CLUSTER of
    at least two adjacent high-impact cells (isolated single cells are not called 'zones')."""
    n_top = max(30, int(len(cells) * top_frac))
    hot = cells.head(n_top).copy()
    coords = np.radians(hot[["lat", "lon"]].values)
    eps = eps_m / 6371000.0  # metres -> radians
    lbl = DBSCAN(eps=eps, min_samples=min_samples, metric="haversine").fit_predict(coords)
    hot["zone"] = lbl

    rows = []
    for z, sub in hot[hot.zone >= 0].groupby("zone"):
        w = sub.cis_raw.values + 1e-9
        rows.append(dict(
            zone_id=int(z),
            name=_mode(sub.area) or _mode(sub.junction) or f"Zone {z}",
            lat=float(np.average(sub.lat, weights=w)),
            lon=float(np.average(sub.lon, weights=w)),
            n_cells=len(sub),
            n_violations=int(sub.n_total.sum()),
            n_parking=int(sub.n_parking.sum()),
            severity_mean=round(float(np.average(sub.severity_mean, weights=w)), 3),
            persistence=round(float(sub.persistence.mean()), 3),
            peak_share=round(float(np.average(sub.peak_share, weights=w)), 3),
            CIS=round(float(sub.cis_raw.sum()), 1),
            top_violation=_mode(sub.top_violation),
            police_station=_mode(sub.police_station),
        ))
    cols = ["zone_id", "name", "lat", "lon", "n_cells", "n_violations", "n_parking",
            "severity_mean", "persistence", "peak_share", "CIS", "top_violation", "police_station"]
    if not rows:
        return pd.DataFrame(columns=cols + ["CIS_100", "zone_rank"])
    zones = pd.DataFrame(rows).sort_values("CIS", ascending=False).reset_index(drop=True)
    zones["CIS_100"] = (100 * zones.CIS / zones.CIS.max()).round(1)
    zones["zone_rank"] = np.arange(1, len(zones) + 1)
    return zones
