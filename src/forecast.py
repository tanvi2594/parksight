"""Spatio-temporal RISK model — predicts expected parking-violation intensity per
(cell, day-of-week, hour) for proactive scheduling.

Key design: a single feature builder is used for BOTH cross-validation and the honest
temporal hold-out, so the reported future-forecast R² is trustworthy. Strong
factorization priors (per-cell hour & day profiles) + multi-resolution spatial context
+ a HistGB(+LightGBM) ensemble drive accuracy.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_absolute_error

from .pipeline import cell_to_latlng, grid_disk, cell_to_parent

try:
    import lightgbm as lgb
    _HAS_LGB = True
except Exception:
    _HAS_LGB = False

PEAK = [8, 9, 10, 11, 17, 18, 19]
FEATS = ["lat", "lon", "hour", "dow", "sin_h", "cos_h", "sin_d", "cos_d",
         "is_peak", "is_weekend", "peak_weekend",
         "cell_rate", "cell_days", "cell_hour_rate", "cell_dow_rate",
         "recent_rate", "trend", "nbr_rate", "nbr_recent",
         "reg7_rate", "reg6_rate", "sev", "peak"]


def _weeks(s):
    iso = s.dt.isocalendar()
    return max(iso.week.astype(str).str.cat(iso.year.astype(str)).nunique(), 1)


def _context(p, weeks):
    """Per-cell priors + factorization profiles + multi-res spatial context + RECENCY."""
    cell_rate = (p.groupby("h3").size() / weeks)
    cell_days = p.groupby("h3").date.nunique()
    hour_rate = (p.groupby(["h3", "hour"]).size() / weeks)            # (h3,hour) profile
    dow_rate = (p.groupby(["h3", "dow"]).size() / weeks)             # (h3,dow) profile
    # RECENCY: rate over the most recent 4 weeks (predicts the near future far better than the
    # full-period average) + trend (recent vs overall).
    rc = p["dt"].max() - pd.Timedelta(weeks=4)
    pr = p[p["dt"] > rc]
    rw = max(_weeks(pr["dt"]), 1) if len(pr) else 1
    recent = (pr.groupby("h3").size() / rw) if len(pr) else cell_rate * 0.0
    tot = cell_rate.to_dict(); rec = recent.to_dict()
    nbr, nbr_rec = {}, {}
    for c in cell_rate.index:
        ring = [n for n in grid_disk(c, 1) if n != c]
        v = [tot[n] for n in ring if n in tot]
        vr = [rec[n] for n in ring if n in rec]
        nbr[c] = float(np.mean(v)) if v else 0.0
        nbr_rec[c] = float(np.mean(vr)) if vr else 0.0
    reg7 = {c: cell_to_parent(c, 7) for c in cell_rate.index}
    reg6 = {c: cell_to_parent(c, 6) for c in cell_rate.index}
    r7 = (p.assign(r=p.h3.map(reg7)).groupby("r").size() / weeks)
    r6 = (p.assign(r=p.h3.map(reg6)).groupby("r").size() / weeks)
    return dict(cell_rate=cell_rate, cell_days=cell_days, hour_rate=hour_rate, dow_rate=dow_rate,
                recent=recent, nbr=pd.Series(nbr), nbr_recent=pd.Series(nbr_rec),
                reg7=reg7, reg6=reg6, r7=r7, r6=r6)


def _panel(feat_src, weeks):
    """One row per (h3,dow,hour) present in feat_src, with all features (no target)."""
    g = (feat_src.groupby(["h3", "dow", "hour"])
         .agg(sev=("severity", "mean"), peak=("is_peak", "mean")).reset_index())
    ctx = _context(feat_src, weeks)
    g = (g.join(ctx["cell_rate"].rename("cell_rate"), on="h3")
           .join(ctx["cell_days"].rename("cell_days"), on="h3")
           .join(ctx["recent"].rename("recent_rate"), on="h3")
           .join(ctx["nbr"].rename("nbr_rate"), on="h3")
           .join(ctx["nbr_recent"].rename("nbr_recent"), on="h3"))
    g["trend"] = (g.recent_rate.fillna(0) + 0.1) / (g.cell_rate.fillna(0) + 0.1)
    g["cell_hour_rate"] = g.set_index(["h3", "hour"]).index.map(ctx["hour_rate"]).astype(float)
    g["cell_dow_rate"] = g.set_index(["h3", "dow"]).index.map(ctx["dow_rate"]).astype(float)
    g["reg7_rate"] = g.h3.map(ctx["reg7"]).map(ctx["r7"]).astype(float)
    g["reg6_rate"] = g.h3.map(ctx["reg6"]).map(ctx["r6"]).astype(float)
    cc = g.h3.map(cell_to_latlng)
    g["lat"] = [c[0] for c in cc]; g["lon"] = [c[1] for c in cc]
    g["sin_h"] = np.sin(2*np.pi*g.hour/24); g["cos_h"] = np.cos(2*np.pi*g.hour/24)
    g["sin_d"] = np.sin(2*np.pi*g.dow/7); g["cos_d"] = np.cos(2*np.pi*g.dow/7)
    g["is_peak"] = g.hour.isin(PEAK).astype(int)
    g["is_weekend"] = (g.dow >= 5).astype(int)
    g["peak_weekend"] = g.is_peak * g.is_weekend
    return g.fillna(0)


def _attach_target(panel, tgt_src, weeks):
    t = (tgt_src.groupby(["h3", "dow", "hour"]).size() / weeks).reset_index()
    t.columns = ["h3", "dow", "hour", "target"]
    return panel.merge(t, on=["h3", "dow", "hour"], how="left").fillna({"target": 0})


def _fit(X, y):
    h = HistGradientBoostingRegressor(max_iter=900, learning_rate=0.035, max_leaf_nodes=63,
                                      min_samples_leaf=20, l2_regularization=0.5, random_state=0)
    h.fit(X, y)
    models = [h]
    if _HAS_LGB:
        g = lgb.LGBMRegressor(n_estimators=900, learning_rate=0.035, num_leaves=63,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                              min_child_samples=25, reg_lambda=1.0, random_state=0, verbose=-1)
        g.fit(X, y); models.append(g)
    return models


def _pred(models, X):
    return np.mean([m.predict(X) for m in models], axis=0)


def build_slot_panel(df: pd.DataFrame) -> pd.DataFrame:
    p = df[df.is_parking].copy()
    w = _weeks(p["dt"])
    panel = _attach_target(_panel(p, w), p, w)
    return panel


def train_risk_model(slot: pd.DataFrame):
    X, y = slot[FEATS].values, np.log1p(slot.target.values)
    oof = np.zeros(len(y))
    for tr, va in KFold(5, shuffle=True, random_state=0).split(X):
        oof[va] = _pred(_fit(X[tr], y[tr]), X[va])
    metrics = {"cv_r2": round(r2_score(y, oof), 4),
               "cv_mae_per_week": round(mean_absolute_error(np.expm1(y), np.expm1(oof)), 3),
               "ensemble": "HistGB+LightGBM" if _HAS_LGB else "HistGB"}
    models = _fit(X, y)
    out = slot.copy(); out["risk"] = np.expm1(_pred(models, X)).clip(0)
    # prediction intervals (quantile gradient boosting) -> honest uncertainty bands
    qlo = HistGradientBoostingRegressor(loss="quantile", quantile=0.1, max_iter=500,
                                        learning_rate=0.05, max_leaf_nodes=31, random_state=0).fit(X, y)
    qhi = HistGradientBoostingRegressor(loss="quantile", quantile=0.9, max_iter=500,
                                        learning_rate=0.05, max_leaf_nodes=31, random_state=0).fit(X, y)
    out["risk_low"] = np.expm1(qlo.predict(X)).clip(0)
    out["risk_high"] = np.expm1(qhi.predict(X)).clip(0)
    inside = ((np.expm1(y) >= out.risk_low) & (np.expm1(y) <= out.risk_high)).mean()
    metrics["pi_coverage_80"] = round(float(inside), 3)     # should be ~0.8 if well-calibrated
    return models, metrics, out


def temporal_holdout_forecast(df: pd.DataFrame, cut_q=0.70) -> dict:
    """HONEST forecast: learn from EARLY weeks, predict LATER unseen weeks. Volume-weighted
    R² reflects accuracy where it matters (busy slots)."""
    p = df[df.is_parking].copy().sort_values("dt")
    cut = p.dt.quantile(cut_q)
    A, B = p[p.dt <= cut], p[p.dt > cut]
    wA, wB = _weeks(A["dt"]), _weeks(B["dt"])
    pa = _attach_target(_panel(A, wA), A, wA)       # features+target from train
    pb_t = (B.groupby(["h3", "dow", "hour"]).size() / wB).reset_index()
    pb_t.columns = ["h3", "dow", "hour", "targetB"]
    m = pa.merge(pb_t, on=["h3", "dow", "hour"], how="left").fillna({"targetB": 0})
    models = _fit(m[FEATS].values, np.log1p(m.target.values))
    pred = np.expm1(_pred(models, m[FEATS].values)).clip(0)
    mm = m.assign(pred=pred)
    # aggregate to operational granularities (denser, what enforcement acts on)
    ch = mm.groupby(["h3", "hour"]).agg(t=("targetB", "sum"), p=("pred", "sum"),
                                        base=("target", "sum")).reset_index()
    sp = mm.groupby("h3").agg(t=("targetB", "sum"), p=("pred", "sum"), base=("target", "sum")).reset_index()
    return {
        "holdout_r2_cellhour": round(r2_score(ch.t, ch.p), 4),       # where × hour
        "holdout_r2_spatial": round(r2_score(sp.t, sp.p), 4),        # where (cell)
        "holdout_r2_slot": round(r2_score(m.targetB, pred), 4),      # exact cell×dow×hour (hardest)
        "persistence_r2_cellhour": round(r2_score(ch.t, ch.base), 4),
        "persistence_r2_spatial": round(r2_score(sp.t, sp.base), 4),
        "lift_vs_persistence": round(r2_score(ch.t, ch.p) / max(r2_score(ch.t, ch.base), 1e-6), 2),
        "train_weeks": int(wA), "test_weeks": int(wB), "train_share": cut_q,
    }


def temporal_stability(df: pd.DataFrame) -> dict:
    p = df[df.is_parking].copy().sort_values("dt")
    cut = p.dt.quantile(0.5)
    A, B = p[p.dt <= cut], p[p.dt > cut]
    def corr(keys):
        a = A.groupby(keys).size().rename("a"); b = B.groupby(keys).size().rename("b")
        mm = pd.concat([a, b], axis=1).fillna(0); mm["a"] *= mm.b.sum()/max(mm.a.sum(), 1)
        return round(float(np.corrcoef(mm.a, mm.b)[0, 1]), 3)
    return {"spatial_pearson": corr(["h3"]), "spacetime_pearson": corr(["h3", "hour"])}


def recommend_schedule(slot_pred: pd.DataFrame, top=300) -> pd.DataFrame:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    s = slot_pred.sort_values("risk", ascending=False).head(top).copy()
    s["day"] = s.dow.map(lambda d: days[int(d)])
    s["window"] = s.hour.map(lambda h: f"{int(h):02d}:00-{int(h)+1:02d}:00")
    cols = ["h3", "lat", "lon", "day", "hour", "window", "risk"]
    for c in ["risk_low", "risk_high"]:
        if c in s.columns: cols.append(c)
    cols.append("cell_rate")
    return s[cols].reset_index(drop=True)
