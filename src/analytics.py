"""Advanced enforcement analytics:
  - repeat-offender intelligence (vehicle_number)
  - emerging-hotspot early warning (trend detection)
  - enforcement coverage-gap (demand vs enforcement effort)
  - deploy-&-simulate coverage (used live by the dashboard)
"""
import numpy as np
import pandas as pd

from .config import (DELAY_MIN_FULL_BLOCK, VALUE_OF_TIME_PER_HR, PATROL_SPEED_KMPH,
                     SEVERITY, DEFAULT_SEVERITY)
from .pipeline import cell_to_parent


# ============================ #1 DATA-DRIVEN SEVERITY ============================
def calibrate_severity(df: pd.DataFrame, events: pd.DataFrame, res=7, blend=0.7):
    """Learn each violation type's congestion weight by regressing per-area violation-type
    counts against INDEPENDENT congestion/accident events (non-negative least squares),
    then blend with the hand-set priors for stability. Returns (final_weights, comparison)."""
    from sklearn.linear_model import LinearRegression
    if events is None or not len(events):
        return dict(SEVERITY), pd.DataFrame()
    d = df[df.is_parking].copy()
    d["area"] = [cell_to_parent(h, res) for h in d.h3.values]
    ex = d[["area", "vlist"]].explode("vlist").dropna()
    ct = ex.pivot_table(index="area", columns="vlist", aggfunc="size", fill_value=0)
    # independent congestion/accident events per area
    flow = events[events.event_cause.isin(["congestion", "accident"])].copy()
    flow["area"] = [cell_to_parent_safe(la, lo, res) for la, lo in zip(flow.latitude, flow.longitude)]
    y = flow.groupby("area").size().reindex(ct.index).fillna(0).values
    keep = ct.columns[ct.sum() >= 30]                      # only types with enough signal
    X = ct[keep].values.astype(float)
    if X.shape[1] == 0 or y.sum() == 0:
        return dict(SEVERITY), pd.DataFrame()
    reg = LinearRegression(positive=True).fit(X, y)
    coef = pd.Series(reg.coef_, index=keep)
    learned = (coef / coef.max()).clip(0, 1) if coef.max() > 0 else coef
    final, rows = dict(SEVERITY), []
    for t in SEVERITY:
        pr = SEVERITY[t]
        if t in learned.index:
            fv = round(blend * pr + (1 - blend) * float(learned[t]), 3)
            final[t] = fv; rows.append({"type": t, "prior": pr, "learned": round(float(learned[t]), 3), "final": fv})
    comp = pd.DataFrame(rows).sort_values("final", ascending=False)
    return final, comp


def cell_to_parent_safe(lat, lon, res):
    from .pipeline import latlng_to_cell
    return cell_to_parent(latlng_to_cell(lat, lon, 9), res)


def recompute_severity(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Recompute per-row severity / top_violation from a (calibrated) weights dict."""
    df = df.copy()
    df["severity"] = df.vlist.map(lambda L: max([weights.get(v, DEFAULT_SEVERITY) for v in L], default=DEFAULT_SEVERITY))
    df["top_violation"] = df.vlist.map(
        lambda L: max(L, key=lambda v: weights.get(v, DEFAULT_SEVERITY)) if L else "UNKNOWN")
    return df


# ============================ #2 ENFORCEMENT-BIAS CORRECTION =====================
def demand_adjusted(cells: pd.DataFrame, df: pd.DataFrame, lam=0.6):
    """Caught violations under-count where enforcement rarely goes. Estimate the underlying
    demand by inflating impact in low-enforcement cells: adj = CIS * (1 + lam*(1 - effort_pct))."""
    p = df[df.is_parking]
    eff = p.groupby("h3").agg(enf_days=("date", "nunique"), officers=("created_by_id", "nunique"))
    c = cells.merge(eff, on="h3", how="left").fillna({"enf_days": 0, "officers": 0})
    c["effort"] = c.enf_days + 0.5 * c.officers
    c["effort_pct"] = c.effort.rank(pct=True)
    c["CIS_adj"] = (c.CIS * (1 + lam * (1 - c.effort_pct))).clip(0, 100).round(2)
    c["hidden_uplift_%"] = (100 * (c.CIS_adj - c.CIS) / c.CIS.replace(0, np.nan)).round(0)
    return c[["h3", "lat", "lon", "area", "CIS", "CIS_adj", "hidden_uplift_%", "enf_days", "police_station"]]


# ---------------------------------------------------------------- repeat offenders
def repeat_offenders(df: pd.DataFrame):
    """Concentration of violations across vehicles + worst chronic offenders."""
    p = df[df.is_parking].copy()
    p = p[p.vehicle_number.notna() & (p.vehicle_number.astype(str).str.len() > 3)]
    vc = p.vehicle_number.value_counts()
    n_veh, n_vio = len(vc), int(vc.sum())

    cum = vc.cumsum() / n_vio                       # vc already sorted desc
    pareto = pd.DataFrame({"veh_frac": np.arange(1, n_veh + 1) / n_veh, "vio_cov": cum.values})

    def share_at(vf):
        return round(100 * pareto.vio_cov.iloc[min(int(vf * n_veh), n_veh - 1)], 1)

    top_ids = vc.head(25).index
    top = vc.head(25).rename_axis("vehicle_number").reset_index(name="violations")
    # enrich ONLY the top offenders (fast)
    sub = p[p.vehicle_number.isin(top_ids)]
    info = sub.groupby("vehicle_number").agg(
        vehicle_type=("vehicle_type", lambda s: s.mode().iloc[0] if len(s.mode()) else None),
        top_violation=("top_violation", lambda s: s.mode().iloc[0] if len(s.mode()) else None),
        police_station=("police_station", lambda s: s.mode().iloc[0] if len(s.mode()) else None),
        days_active=("date", "nunique"))
    top = top.join(info, on="vehicle_number")

    stats = {
        "n_vehicles": n_veh, "n_violations": n_vio,
        "repeat_share_%": round(100 * (vc >= 2).mean(), 1),
        "vio_from_repeat_%": round(100 * vc[vc >= 2].sum() / n_vio, 1),
        "share_top1pct": share_at(0.01), "share_top5pct": share_at(0.05),
        "share_top10pct": share_at(0.10), "max_by_one_vehicle": int(vc.max()),
    }
    return stats, pareto, top


# ---------------------------------------------------------------- congestion cost (₹)
def congestion_cost(cells: pd.DataFrame, days: int):
    """Monetise parking-induced delay. Per violation: severity × DELAY_MIN_FULL_BLOCK
    vehicle-minutes, valued at VALUE_OF_TIME_PER_HR. Annualised from the sample window."""
    ann = 365.0 / max(days, 1)
    veh_min = cells.n_parking * cells.severity_mean * DELAY_MIN_FULL_BLOCK
    cost_year = veh_min * (VALUE_OF_TIME_PER_HR / 60.0) * ann
    c = cells.assign(cost_year=cost_year)
    total = float(cost_year.sum())
    top = c.sort_values("cost_year", ascending=False)
    top10_share = round(100 * top.cost_year.head(int(len(c) * 0.10)).sum() / total, 1)
    # ILLUSTRATIVE range: vary the two assumptions (delay 8-16 veh-min, VoT ₹150-350/hr)
    lo = total * (8 / DELAY_MIN_FULL_BLOCK) * (150 / VALUE_OF_TIME_PER_HR)
    hi = total * (16 / DELAY_MIN_FULL_BLOCK) * (350 / VALUE_OF_TIME_PER_HR)
    return {
        "annual_cost_cr": round(total / 1e7, 2),                 # ₹ crore / year (central)
        "annual_cost_cr_low": round(lo / 1e7, 2),
        "annual_cost_cr_high": round(hi / 1e7, 2),
        "annual_cost_inr": int(total),
        "top10pct_cost_share_%": top10_share,
        "cost_per_day_lakh": round(total / 365 / 1e5, 2),
        "assumptions": f"{DELAY_MIN_FULL_BLOCK:.0f} veh-min/full-block · ₹{VALUE_OF_TIME_PER_HR:.0f}/veh-hr (illustrative)",
    }, c[["h3", "lat", "lon", "area", "cost_year", "CIS", "n_parking"]]


# ---------------------------------------------------------------- patrol routing
def _haversine(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(np.radians, [a[0], a[1], b[0], b[1]])
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(h))


def zone_trends(df: pd.DataFrame, cells: pd.DataFrame):
    """POST-ENFORCEMENT LEARNING LOOP. Track each hotspot's monthly violation trend so an
    intervention can be MEASURED: zones that are improving (problem receding) vs worsening.
    Uses only FULL months (drops partial first/last) for a fair slope."""
    p = df[df.is_parking].copy()
    p["month"] = p.dt.dt.to_period("M").astype(str)
    months = sorted(p.month.unique())
    full = months[1:-1] if len(months) > 2 else months          # drop partial edges
    p = p[p.month.isin(full)]
    mi = {m: i for i, m in enumerate(full)}
    g = p.groupby(["h3", "month"]).size().rename("n").reset_index()
    g["mx"] = g.month.map(mi)

    def slope(sub):
        return np.polyfit(sub.mx, sub.n, 1)[0] if sub.mx.nunique() >= 3 else np.nan
    sl = g.groupby("h3").apply(slope, include_groups=False).rename("slope")
    base = g.groupby("h3").n.mean().rename("base")
    res = pd.concat([sl, base], axis=1).dropna(subset=["slope"])
    res["pct_per_month"] = (res.slope / res.base.replace(0, np.nan) * 100).round(1)
    res = res.join(cells.set_index("h3")[["area", "lat", "lon", "CIS", "police_station", "n_parking"]])
    res["trend"] = pd.cut(res.pct_per_month, [-1e9, -8, 8, 1e9],
                          labels=["Improving", "Stable", "Worsening"])
    hot = res[res.CIS >= res.CIS.quantile(0.75)]                 # focus on real hotspots
    stats = {
        "months_used": full,
        "improving": int((hot.trend == "Improving").sum()),
        "worsening": int((hot.trend == "Worsening").sum()),
        "stable": int((hot.trend == "Stable").sum()),
        "net_worsening_pct": round(100 * ((hot.trend == "Worsening").mean()
                                          - (hot.trend == "Improving").mean()), 1),
    }
    city = g.groupby("month").n.sum().reindex(full).reset_index().rename(columns={"n": "violations"})
    res = res.reset_index().sort_values("pct_per_month")
    return stats, res, city


def deterrence(df: pd.DataFrame) -> dict:
    """Do repeat offenders slow down after repeated catches? (Is current enforcement a
    deterrent?) Compares the gap between early vs later catches for habitual vehicles."""
    p = df[df.is_parking].dropna(subset=["vehicle_number"]).copy()
    p = p[p.vehicle_number.astype(str).str.len() > 3].sort_values("dt")
    cnt = p.groupby("vehicle_number").id.transform("size")
    sub = p[cnt >= 3].copy()
    sub["gap"] = sub.groupby("vehicle_number").dt.diff().dt.total_seconds() / 86400
    sub["occ"] = sub.groupby("vehicle_number").cumcount()
    early = float(sub[sub.occ.isin([1, 2])].gap.median())
    late = float(sub[sub.occ >= 4].gap.median())
    return {
        "habitual_vehicles": int(sub.vehicle_number.nunique()),
        "median_gap_early_days": round(early, 1),
        "median_gap_late_days": round(late, 1),
        "deters": bool(late > early * 1.15),
    }


def ward_rollup(cells: pd.DataFrame, zones: pd.DataFrame, total_force=60):
    """Command-level resource allocation: rank police stations by congestion impact and
    recommend how many of `total_force` patrol units each should get (impact-proportional)."""
    g = cells.groupby("police_station").agg(
        impact=("cis_raw", "sum"), violations=("n_parking", "sum"),
        hotspots=("h3", "size"), chronic=("class", lambda s: int((s == "Chronic").sum()))
    ).reset_index().dropna(subset=["police_station"])
    g = g[g.police_station.astype(str).str.len() > 0]
    g["impact_share_%"] = (100 * g.impact / g.impact.sum()).round(1)
    # proportional allocation with at least 1 unit to any station that has chronic hotspots
    raw = total_force * g.impact / g.impact.sum()
    g["recommended_units"] = np.maximum(np.round(raw).astype(int), (g.chronic > 0).astype(int))
    g = g.sort_values("impact", ascending=False).reset_index(drop=True)
    g["rank"] = np.arange(1, len(g) + 1)
    return g[["rank", "police_station", "impact_share_%", "violations", "hotspots",
              "chronic", "recommended_units"]]


def optimize_coverage(zones: pd.DataFrame, k: int, radius_km=1.2):
    """MAX-COVERAGE patrol placement (submodular greedy, ~(1-1/e) optimal). Each patrol
    covers its zone + zones within `radius_km`; we pick k patrols to maximise the UNION of
    congestion-impact covered (no double-counting) — strictly better than ranking by score,
    because it avoids stacking patrols on overlapping hotspots. Returns chosen zones + stats."""
    z = zones.reset_index(drop=True)
    n = len(z)
    if n == 0:
        return z.head(0), {"opt_cov": 0, "naive_cov": 0, "uplift_pp": 0}
    pts = np.radians(z[["lat", "lon"]].values); imp = z["CIS"].values.astype(float)
    R = 6371.0
    cover = []
    for i in range(n):
        dlat = pts[:, 0] - pts[i, 0]; dlon = pts[:, 1] - pts[i, 1]
        a = np.sin(dlat/2)**2 + np.cos(pts[i, 0])*np.cos(pts[:, 0])*np.sin(dlon/2)**2
        d = 2*R*np.arcsin(np.sqrt(a))
        cover.append(set(np.where(d <= radius_km)[0]))
    total = imp.sum()
    # greedy submodular max-coverage
    chosen, covered = [], set()
    for _ in range(min(k, n)):
        best, gain = -1, -1.0
        for i in range(n):
            if i in chosen:
                continue
            g = imp[list(cover[i] - covered)].sum()
            if g > gain:
                gain, best = g, i
        if best < 0 or gain <= 0:
            break
        chosen.append(best); covered |= cover[best]
    opt_cov = imp[list(covered)].sum() / total
    # naive: top-k by score (may overlap)
    topk = list(np.argsort(-imp)[:k])
    ncov = set().union(*[cover[i] for i in topk]) if topk else set()
    naive_cov = imp[list(ncov)].sum() / total
    stats = {"opt_cov": round(100*opt_cov, 1), "naive_cov": round(100*naive_cov, 1),
             "uplift_pp": round(100*(opt_cov - naive_cov), 1), "radius_km": radius_km}
    return z.iloc[chosen].copy(), stats


def emergence_prediction(df: pd.DataFrame, cells: pd.DataFrame):
    """PREDICT where new hotspots will EMERGE (the thing persistence can't do). Split the
    timeline into thirds A|B|C. Train on (features from A -> did the cell surge A→B?), and
    validate OUT-OF-TIME on (features from B -> surge B→C). Reports ROC-AUC + precision."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from .pipeline import grid_disk
    p = df[df.is_parking].sort_values("dt")
    q1, q2 = p.dt.quantile(1/3), p.dt.quantile(2/3)
    cA = p[p.dt <= q1].groupby("h3").size()
    cB = p[(p.dt > q1) & (p.dt <= q2)].groupby("h3").size()
    cC = p[p.dt > q2].groupby("h3").size()
    allc = cells.h3.values

    def feat(c):
        d = c.to_dict(); rows = []
        for h in allc:
            lvl = d.get(h, 0)
            ring = [d.get(n, 0) for n in grid_disk(h, 1) if n != h]
            rows.append([lvl, np.log1p(lvl), float(np.mean(ring)) if ring else 0.0,
                         float(np.max(ring)) if ring else 0.0])
        return np.array(rows)

    def label(cur, nxt):
        cu, nx = cur.to_dict(), nxt.to_dict()
        return np.array([1 if (nx.get(h, 0) > 1.3*cu.get(h, 0) and nx.get(h, 0)-cu.get(h, 0) >= 5)
                         else 0 for h in allc])

    Xtr, ytr = feat(cA), label(cA, cB)
    Xte, yte = feat(cB), label(cB, cC)
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, random_state=0)
    m.fit(Xtr, ytr)
    proba = m.predict_proba(Xte)[:, 1]
    auc = float(roc_auc_score(yte, proba)) if len(set(yte)) > 1 else float("nan")
    k = max(int(0.05 * len(proba)), 1)
    top = np.argsort(-proba)[:k]
    prec = float(yte[top].mean())
    base = float(yte.mean())
    # forward: predict next emergers from the latest window
    pc = m.predict_proba(feat(cC))[:, 1]
    pred = (pd.DataFrame({"h3": allc, "emergence_prob": np.round(pc, 3)})
            .merge(cells[["h3", "area", "lat", "lon", "CIS", "police_station"]], on="h3")
            .sort_values("emergence_prob", ascending=False).head(20).reset_index(drop=True))
    stats = {"auc": round(auc, 3), "precision_top5pct": round(prec, 3),
             "base_rate": round(base, 3),
             "lift": round(prec / base, 1) if base > 0 else None, "n_surges": int(yte.sum())}
    return stats, pred


def patrol_route(chosen: pd.DataFrame):
    """Nearest-neighbour visiting order over assigned zones + total distance/ETA."""
    pts = chosen[["lat", "lon"]].values
    if len(pts) <= 1:
        return chosen.assign(stop=range(1, len(chosen) + 1)), 0.0, 0.0
    unvisited = list(range(len(pts)))
    order = [unvisited.pop(0)]            # start at highest-impact zone
    while unvisited:
        last = pts[order[-1]]
        nxt = min(unvisited, key=lambda i: _haversine(last, pts[i]))
        order.append(nxt); unvisited.remove(nxt)
    dist = sum(_haversine(pts[order[i]], pts[order[i + 1]]) for i in range(len(order) - 1))
    routed = chosen.iloc[order].copy(); routed["stop"] = range(1, len(routed) + 1)
    eta = 60 * dist / PATROL_SPEED_KMPH
    return routed, round(dist, 1), round(eta, 0)


# ---------------------------------------------------------------- emerging hotspots
def emerging_hotspots(df: pd.DataFrame, cells: pd.DataFrame, recent_frac=0.25):
    """Flag cells whose violation rate is RISING: compare the most recent window to the
    baseline period (rate per day), and rank by growth. Early warning before chronic."""
    p = df[df.is_parking].copy().sort_values("dt")
    cut = p.dt.quantile(1 - recent_frac)
    base_days = max((cut - p.dt.min()).days, 1)
    rec_days = max((p.dt.max() - cut).days, 1)

    base = p[p.dt <= cut].groupby("h3").size().rename("base_n")
    rec = p[p.dt > cut].groupby("h3").size().rename("rec_n")
    g = pd.concat([base, rec], axis=1).fillna(0)
    g["base_rate"] = g.base_n / base_days
    g["rec_rate"] = g.rec_n / rec_days
    g["growth"] = (g.rec_rate + 0.02) / (g.base_rate + 0.02)        # smoothed ratio
    g["delta_per_day"] = (g.rec_rate - g.base_rate).round(3)
    g = g.join(cells.set_index("h3")[["lat", "lon", "area", "police_station",
                                      "CIS", "top_violation", "n_total"]])
    # emerging = meaningful volume, strong growth, not already saturated-chronic
    em = g[(g.rec_n >= 8) & (g.growth >= 1.6)].copy()
    em["growth_x"] = em.growth.round(2)
    em = em.sort_values(["growth", "rec_rate"], ascending=False)
    cols = ["lat", "lon", "area", "police_station", "growth_x", "delta_per_day",
            "base_rate", "rec_rate", "rec_n", "CIS", "top_violation"]
    return em[cols].reset_index().rename(columns={"index": "h3"})


# ---------------------------------------------------------------- coverage gap
def coverage_gap(df: pd.DataFrame, cells: pd.DataFrame):
    """Under-enforced hotspots: high congestion impact (demand) but low enforcement
    EFFORT (distinct enforcement days / officers). Gap = demand_pct - effort_pct."""
    p = df[df.is_parking].copy()
    eff = p.groupby("h3").agg(enf_days=("date", "nunique"),
                              officers=("created_by_id", "nunique"),
                              devices=("device_id", "nunique")).reset_index()
    c = cells.merge(eff, on="h3", how="left").fillna({"enf_days": 0, "officers": 0, "devices": 0})
    c["effort"] = c.enf_days + 0.5 * c.officers
    c["demand_pct"] = c.CIS.rank(pct=True)
    c["effort_pct"] = c.effort.rank(pct=True)
    c["gap"] = (c.demand_pct - c.effort_pct).round(3)           # >0 => under-enforced
    c["intensity_per_visit"] = (c.n_parking / c.enf_days.replace(0, np.nan)).round(1)
    under = c[(c.CIS >= c.CIS.quantile(0.80)) & (c.gap > 0.15)].copy()
    under = under.sort_values("gap", ascending=False)
    cols = ["h3", "lat", "lon", "area", "police_station", "CIS", "n_parking",
            "enf_days", "officers", "intensity_per_visit", "gap"]
    stats = {
        "n_under_enforced": int(len(under)),
        "median_enf_days_top_hotspots": float(c[c.CIS >= c.CIS.quantile(0.9)].enf_days.median()),
        "corr_demand_effort": round(float(np.corrcoef(c.demand_pct, c.effort_pct)[0, 1]), 3),
    }
    return stats, under[cols].reset_index(drop=True), c[["lat", "lon", "CIS", "gap", "area"]]


# ---------------------------------------------------------------- deploy & simulate
def simulate_deployment(zones: pd.DataFrame, n_units: int):
    """What does deploying n patrol units to the top-impact zones achieve?"""
    total = zones.CIS.sum()
    z = zones.sort_values("CIS", ascending=False).reset_index(drop=True)
    chosen = z.head(n_units)
    return {
        "units": int(n_units),
        "zones_covered": int(len(chosen)),
        "impact_covered_%": round(100 * chosen.CIS.sum() / total, 1),
        "violations_covered": int(chosen.n_parking.sum()),
        "violations_covered_%": round(100 * chosen.n_parking.sum() / zones.n_parking.sum(), 1),
        "chosen": chosen,
    }
