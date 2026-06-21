"""Turn impact scores into ACTION: prioritise zones, quantify enforcement ROI
(Pareto coverage), and produce a capacity-constrained patrol plan."""
import numpy as np
import pandas as pd


def pareto_coverage(cells: pd.DataFrame) -> pd.DataFrame:
    """Cumulative share of total congestion-impact (and of all violations) covered
    as we enforce the top-N highest-impact cells. The core ROI argument."""
    c = cells.sort_values("cis_raw", ascending=False).reset_index(drop=True)
    out = pd.DataFrame({
        "n_zones": np.arange(1, len(c) + 1),
        "zone_frac": (np.arange(1, len(c) + 1) / len(c)),
        "impact_cov": c.cis_raw.cumsum() / c.cis_raw.sum(),
        "violation_cov": c.n_parking.cumsum() / c.n_parking.sum(),
    })
    return out


def roi_headline(pareto: pd.DataFrame) -> dict:
    """Key one-liners for the pitch deck."""
    def cov_at(frac):
        row = pareto.iloc[(pareto.zone_frac - frac).abs().idxmin()]
        return round(100 * row.impact_cov, 1)
    def zones_for(target):
        hit = pareto[pareto.impact_cov >= target]
        return int(hit.n_zones.iloc[0]) if len(hit) else len(pareto)
    return {
        "impact_covered_top5pct_zones": cov_at(0.05),
        "impact_covered_top10pct_zones": cov_at(0.10),
        "zones_for_50pct_impact": zones_for(0.50),
        "zones_for_80pct_impact": zones_for(0.80),
        "total_cells": int(len(pareto)),
    }


def allocate_patrols(zones: pd.DataFrame, n_patrols=15) -> pd.DataFrame:
    """Assign N patrol units to the top-N zones by impact; report marginal coverage."""
    z = zones.sort_values("CIS", ascending=False).head(n_patrols).copy().reset_index(drop=True)
    total = zones.CIS.sum()
    z["patrol_id"] = np.arange(1, len(z) + 1)
    z["impact_share_%"] = (100 * z.CIS / total).round(2)
    z["cum_impact_%"] = z["impact_share_%"].cumsum().round(2)
    cols = ["patrol_id", "name", "lat", "lon", "n_parking", "CIS",
            "impact_share_%", "cum_impact_%", "top_violation", "police_station"]
    return z[[c for c in cols if c in z.columns]]
