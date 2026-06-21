"""'Ask ParkSight' — a lightweight, fully-offline natural-language layer over the
precomputed intelligence. Parses intent + place + day + time and answers in plain
English, returning a result table and a map focus. No external API required."""
import re
import numpy as np
import pandas as pd

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAYFULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _parse_day(q):
    for i, d in enumerate(DAYS):
        if d in q or DAYFULL[i].lower() in q:
            return i
    if "weekend" in q:
        return 6
    return None


def _parse_hour(q):
    m = re.search(r"(\d{1,2})\s*(am|pm)", q)
    if m:
        h = int(m.group(1)) % 12
        return h + (12 if m.group(2) == "pm" else 0)
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", q)
    if m:
        return int(m.group(1))
    for k, h in {"morning": 9, "noon": 12, "afternoon": 15, "evening": 18, "night": 22}.items():
        if k in q:
            return h
    return None


def _match_place(q, cells, zones):
    cands = pd.unique(pd.concat([zones.name.astype(str), cells.area.astype(str),
                                 cells.police_station.astype(str)]).dropna())
    cands = sorted([c for c in cands if isinstance(c, str) and len(c) > 3], key=len, reverse=True)
    for c in cands:
        if c.lower() in q:
            return c
    return None


def answer(query, cells, zones, slot, M):
    q = query.lower().strip()
    day, hour, place = _parse_day(q), _parse_hour(q), _match_place(q, cells, zones)
    res = pd.DataFrame()
    focus = None

    # ---- intent: cost ----
    if any(w in q for w in ["cost", "rupee", "₹", "economic", "money"]):
        c = M.get("cost", {})
        return (f"Parking-induced congestion costs an estimated **₹{c.get('annual_cost_cr','?')} crore/year**, "
                f"with **{c.get('top10pct_cost_share_%','?')}%** concentrated in just the top 10% of cells — "
                f"so targeted enforcement captures most of the savings."), res, focus

    # ---- intent: repeat offenders ----
    if any(w in q for w in ["offender", "repeat", "habitual", "vehicle"]):
        o = M.get("offenders", {})
        return (f"**{o.get('vio_from_repeat_%','?')}%** of violations come from repeat vehicles "
                f"(caught ≥2×); the worst single vehicle was booked **{o.get('max_by_one_vehicle','?')}×**. "
                f"Targeted notices/towing of habitual offenders would cut a large share of violations."), res, focus

    # ---- intent: metro / market context ----
    if any(w in q for w in ["metro", "market", "mall", "commercial", "transit"]):
        p = M.get("poi", {})
        return (f"**{p.get('pct_top_near_poi','?')}%** of the top hotspots sit within "
                f"{p.get('radius_m','?')} m of a metro station, market or mall — parking congestion "
                f"clusters tightly around commercial & transit nodes."), res, focus

    # ---- intent: deploy / where / hotspot (default) ----
    pool = zones.copy()
    scope = "city-wide"
    if place:
        mask = (pool.name.astype(str).str.contains(place, case=False, na=False) |
                pool.police_station.astype(str).str.contains(place, case=False, na=False))
        if mask.any():
            pool = pool[mask]; scope = f"near **{place}**"
        else:
            ref = cells[cells.area.astype(str).str.contains(place, case=False, na=False)]
            if len(ref):
                la, lo = ref.lat.mean(), ref.lon.mean()
                d = np.hypot(pool.lat - la, pool.lon - lo)
                pool = pool[d < 0.03]; scope = f"near **{place}**"   # ~3 km

    when = ""
    if (day is not None or hour is not None) and slot is not None:
        base = slot.copy()
        if place and len(pool):
            la, lo = pool.lat.mean(), pool.lon.mean()
            base = base[np.hypot(base.lat - la, base.lon - lo) < 0.03]
        # relax progressively so a useful answer always comes back (evening hrs are sparse)
        if day is not None:
            when += f" on **{DAYFULL[day]}**"
        if hour is not None:
            when += f" around **{hour:02d}:00**"
        trials = []
        if day is not None and hour is not None:
            trials.append(base[(base.dow == day) & (base.hour == hour)])
        if day is not None:
            trials.append(base[base.dow == day])
        trials.append(base)
        s = next((t for t in trials if len(t) >= 3), trials[-1])
        s = s.merge(cells[["h3", "area", "police_station"]], on="h3", how="left").sort_values("risk", ascending=False)
        res = (s.head(8)[["area", "police_station", "risk", "lat", "lon"]]
               .rename(columns={"area": "Area", "police_station": "Station", "risk": "Pred. viol."}))
        res["Pred. viol."] = res["Pred. viol."].round(1)
        if len(s):
            focus = (float(s.lat.iloc[0]), float(s.lon.iloc[0]))
        top = res.Area.iloc[0] if len(res) else "—"
        return (f"Deploy patrols {scope}{when}. The model's top-risk zone is **{top}**; "
                f"the table lists the {len(res)} highest-risk spots to pre-position units."), res, focus

    # fallback: top hotspots by impact
    pool = pool.sort_values("CIS", ascending=False)
    res = (pool.head(8)[["name", "CIS_100", "n_parking", "top_violation", "police_station", "lat", "lon"]]
           .rename(columns={"name": "Zone", "CIS_100": "Impact", "n_parking": "Viol.",
                            "top_violation": "Dominant", "police_station": "Station"}))
    if len(pool):
        focus = (float(pool.lat.iloc[0]), float(pool.lon.iloc[0]))
    return (f"Highest-impact illegal-parking zones {scope}: **{res.Zone.iloc[0] if len(res) else '—'}** "
            f"tops the list. The table shows the worst {len(res)} for targeted enforcement."), res, focus
