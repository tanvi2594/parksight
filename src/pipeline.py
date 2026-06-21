"""Load + clean the raw violations CSV into a tidy, feature-rich table."""
import ast
import numpy as np
import pandas as pd
import h3

from .config import (RAW_CSV, DATA, TZ, H3_RES, PEAK_HOURS, SEVERITY,
                     DEFAULT_SEVERITY, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX)

# --- h3 v3/v4 compatibility shim --------------------------------------------
def latlng_to_cell(lat, lng, res):
    if hasattr(h3, "latlng_to_cell"):          # h3 >= 4
        return h3.latlng_to_cell(lat, lng, res)
    return h3.geo_to_h3(lat, lng, res)          # h3 == 3

def cell_to_latlng(cell):
    if hasattr(h3, "cell_to_latlng"):
        return h3.cell_to_latlng(cell)
    return h3.h3_to_geo(cell)

def grid_disk(cell, k=1):
    if hasattr(h3, "grid_disk"):
        return h3.grid_disk(cell, k)
    return h3.k_ring(cell, k)

def cell_to_parent(cell, res):
    if hasattr(h3, "cell_to_parent"):
        return h3.cell_to_parent(cell, res)
    return h3.h3_to_parent(cell, res)

def cell_to_boundary(cell):
    """Return hexagon vertices as a list of (lat, lng)."""
    if hasattr(h3, "cell_to_boundary"):
        return list(h3.cell_to_boundary(cell))
    return list(h3.h3_to_geo_boundary(cell))


def _parse_list(x):
    if isinstance(x, str) and x.startswith("["):
        try:
            return [str(s).strip() for s in ast.literal_eval(x)]
        except Exception:
            return []
    return []


def load_clean(force=False) -> pd.DataFrame:
    """Return the cleaned, feature-engineered violations dataframe (cached)."""
    cache = DATA / "clean.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    usecols = ["id", "latitude", "longitude", "location", "vehicle_type",
               "violation_type", "created_datetime", "junction_name", "police_station",
               "vehicle_number", "device_id", "created_by_id", "validation_status"]
    df = pd.read_csv(RAW_CSV, usecols=usecols)

    # --- geo clean ---
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[(df.latitude.between(LAT_MIN, LAT_MAX)) & (df.longitude.between(LON_MIN, LON_MAX))]

    # --- time ---
    dt = pd.to_datetime(df.created_datetime, errors="coerce", utc=True).dt.tz_convert(TZ)
    df = df.assign(dt=dt).dropna(subset=["dt"])
    df["date"] = df.dt.dt.date
    df["hour"] = df.dt.dt.hour
    df["dow"] = df.dt.dt.dayofweek                 # 0=Mon
    df["is_weekend"] = df.dow >= 5
    df["is_peak"] = df.hour.isin(PEAK_HOURS)

    # --- violation parsing + severity ---
    vlist = df.violation_type.map(_parse_list)
    df["vlist"] = vlist
    df["n_violations"] = vlist.map(len)
    df["severity"] = vlist.map(lambda L: max([SEVERITY.get(v, DEFAULT_SEVERITY) for v in L], default=DEFAULT_SEVERITY))
    df["is_parking"] = vlist.map(lambda L: any("PARK" in v for v in L))
    df["top_violation"] = vlist.map(lambda L: max(L, key=lambda v: SEVERITY.get(v, DEFAULT_SEVERITY)) if L else "UNKNOWN")

    # --- spatial index (H3) ---
    df["h3"] = [latlng_to_cell(la, lo, H3_RES) for la, lo in zip(df.latitude.values, df.longitude.values)]

    df = df.reset_index(drop=True)
    df.drop(columns=["violation_type", "created_datetime"]).to_parquet(cache, index=False)
    return df


if __name__ == "__main__":
    d = load_clean(force=True)
    print("clean rows:", len(d))
    print(d[["dt", "hour", "dow", "severity", "is_parking", "top_violation", "h3"]].head())
    print("date span:", d.date.min(), "->", d.date.max(), "| days:", d.date.nunique())
    print("parking share: %.1f%%" % (100 * d.is_parking.mean()))
