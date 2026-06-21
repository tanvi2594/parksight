"""CROSS-DATASET VALIDATION (the differentiator).

We validate the Congestion-Impact Score against an INDEPENDENT dataset (Astram
event log: live congestion / accident / breakdown reports). If our illegal-parking
hotspots are real traffic chokepoints, then independently-reported congestion &
accident events should cluster in our high-CIS cells far more than chance.
"""
import numpy as np
import pandas as pd

from .config import EVENTS_CSV, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX
from .pipeline import latlng_to_cell, load_clean

# Independent congestion/accident reports = ground-truth flow disruption.
FLOW_CAUSES = {"congestion", "accident"}
VR = 7          # validation aggregation resolution (~1.2 km neighbourhoods)
VR_NBHD = 6     # coarser neighbourhood resolution for the headline correlation


def load_events() -> pd.DataFrame:
    if not EVENTS_CSV.exists():
        return pd.DataFrame()
    e = pd.read_csv(EVENTS_CSV, usecols=["latitude", "longitude", "event_cause",
                                         "event_type", "requires_road_closure"])
    e = e.dropna(subset=["latitude", "longitude"])
    e = e[(e.latitude.between(LAT_MIN, LAT_MAX)) & (e.longitude.between(LON_MIN, LON_MAX))]
    return e


def _area_cis(df, res):
    """Parking Congestion-Impact aggregated to res-`res` areas."""
    p = df[df.is_parking]
    k = [latlng_to_cell(a, o, res) for a, o in zip(p.latitude.values, p.longitude.values)]
    t = pd.DataFrame({"k": k, "sev": p.severity.values})
    g = t.groupby("k").agg(park=("sev", "size"), sev=("sev", "mean"))
    g["cis"] = g.park * g.sev
    return g


def validate_against_events(cells: pd.DataFrame = None) -> dict:
    """Validate the Impact Score against INDEPENDENT congestion/accident events,
    aggregated to neighbourhood areas (res-9 cells are too fine for sparse events)."""
    e = load_events()
    if e.empty:
        return {"available": False}
    df = load_clean()
    flow = e[e.event_cause.isin(FLOW_CAUSES)].copy()

    def stats(res):
        area = _area_cis(df, res)
        ek = pd.Series([latlng_to_cell(a, o, res) for a, o in zip(flow.latitude, flow.longitude)]).value_counts()
        m = area.join(ek.rename("ev")).fillna({"ev": 0})
        m["dec"] = pd.qcut(m.cis.rank(method="first"), 10, labels=False) + 1
        top = float(m[m.dec >= 9].ev.sum() / max(m.ev.sum(), 1))
        pear = float(np.corrcoef(np.log1p(m.cis), np.log1p(m.ev))[0, 1])
        spear = float(pd.Series(m.cis).corr(pd.Series(m.ev), method="spearman"))
        return m, top, pear, spear

    m7, top7, pear7, spear7 = stats(VR)
    _, top6, pear6, _ = stats(VR_NBHD)

    # CONTROLLED validation (#3): does CIS predict congestion BEYOND raw violation volume?
    # Partial correlation of CIS vs events, controlling for raw parking volume (the activity proxy).
    area = _area_cis(df, VR_NBHD)
    ek = pd.Series([latlng_to_cell(a, o, VR_NBHD) for a, o in zip(flow.latitude, flow.longitude)]).value_counts()
    mc = area.join(ek.rename("ev")).fillna({"ev": 0})
    lv, lc, le = np.log1p(mc.park), np.log1p(mc.cis), np.log1p(mc.ev)
    def partial(y, x, z):
        ry = y - np.polyval(np.polyfit(z, y, 1), z)
        rx = x - np.polyval(np.polyfit(z, x, 1), z)
        return float(np.corrcoef(rx, ry)[0, 1])
    corr_vol = float(np.corrcoef(lv, le)[0, 1])
    corr_cis = float(np.corrcoef(lc, le)[0, 1])
    partial_cis = partial(le.values, lc.values, lv.values)   # CIS vs events | volume

    return {
        "available": True,
        "n_events_total": int(len(e)),
        "n_congestion_accident": int(len(flow)),
        "validation_res": VR,
        "pearson_logCIS_logEvents": round(pear7, 3),
        "spearman": round(spear7, 3),
        "events_in_top20pct_CIS_%": round(100 * top7, 1),
        "lift_vs_random": round(top7 / 0.20, 2),
        "neighbourhood_pearson_res6": round(pear6, 3),
        "neighbourhood_events_top20pct_%": round(100 * top6, 1),
        "neighbourhood_lift": round(top6 / 0.20, 2),
        "corr_volume_only": round(corr_vol, 3),
        "corr_CIS": round(corr_cis, 3),
        "partial_corr_CIS_given_volume": round(partial_cis, 3),
        "decile_event_counts": m7.groupby("dec").ev.sum().astype(int).to_dict(),
    }


def topzone_precision(zones: pd.DataFrame, radius_m=500, top_n=20) -> dict:
    """Quasi precision: share of the top-N enforcement zones that have an INDEPENDENT
    congestion/accident event within `radius_m` (a check that flagged zones are real)."""
    e = load_events()
    if e.empty or not len(zones):
        return {"available": False}
    flow = e[e.event_cause.isin(FLOW_CAUSES)]
    if not len(flow):
        return {"available": False}
    R = 6371000.0
    plat, plon = np.radians(flow.latitude.values), np.radians(flow.longitude.values)
    z = zones.head(top_n)
    hit = 0
    for r in z.itertuples():
        la, lo = np.radians(r.lat), np.radians(r.lon)
        d = 2*R*np.arcsin(np.sqrt(np.sin((plat-la)/2)**2 + np.cos(la)*np.cos(plat)*np.sin((plon-lo)/2)**2))
        if d.min() <= radius_m:
            hit += 1
    return {"available": True, "top_n": int(len(z)), "radius_m": radius_m,
            "precision_%": round(100 * hit / len(z), 1)}
