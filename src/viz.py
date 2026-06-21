"""Map + chart builders (folium HTML, matplotlib PNGs)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap

from .config import OUT

plt.rcParams.update({"figure.dpi": 120, "font.size": 10, "axes.grid": True, "grid.alpha": .25})
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def hex_geojson(cells):
    """GeoJSON FeatureCollection of H3 hexagons (id = h3) for a crisp choropleth map."""
    from .pipeline import cell_to_boundary
    feats = []
    for c in cells.h3.values:
        ring = [[lng, lat] for lat, lng in cell_to_boundary(c)]
        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])
        feats.append({"type": "Feature", "id": c,
                      "geometry": {"type": "Polygon", "coordinates": [ring]}, "properties": {}})
    return {"type": "FeatureCollection", "features": feats}


def _center(cells):
    w = cells.cis_raw + 1e-9
    return [float(np.average(cells.lat, weights=w)), float(np.average(cells.lon, weights=w))]


def hotspot_map(cells, zones, events=None, path=OUT / "map_hotspots.html"):
    m = folium.Map(location=_center(cells), zoom_start=12, tiles="cartodbpositron")
    # impact heat layer (cell centres weighted by CIS)
    HeatMap([[r.lat, r.lon, float(r.CIS)] for r in cells.itertuples()],
            radius=11, blur=9, min_opacity=0.25, name="Congestion-Impact heat").add_to(m)
    # top enforcement zones
    fg = folium.FeatureGroup(name="Top enforcement zones").add_to(m)
    for r in zones.head(30).itertuples():
        folium.CircleMarker(
            [r.lat, r.lon], radius=6 + 10 * (r.CIS / zones.CIS.max()),
            color="#b30000", fill=True, fill_color="#ff3300", fill_opacity=0.7, weight=1,
            popup=folium.Popup(f"<b>#{r.zone_rank} {r.name}</b><br>CIS {r.CIS_100}/100"
                               f"<br>{r.n_parking} parking violations"
                               f"<br>Top: {r.top_violation}"
                               f"<br>PS: {r.police_station}", max_width=260),
        ).add_to(fg)
    # independent congestion/accident events (validation overlay)
    if events is not None and len(events):
        fg2 = folium.FeatureGroup(name="Independent congestion/accident events").add_to(m)
        for r in events.itertuples():
            folium.CircleMarker([r.latitude, r.longitude], radius=2.5, color="#003399",
                                fill=True, fill_opacity=0.6, weight=0).add_to(fg2)
    folium.LayerControl().add_to(m)
    m.save(str(path))
    return path


def chart_hour_dow(df, path=OUT / "chart_temporal.png"):
    p = df[df.is_parking]
    piv = p.pivot_table(index="dow", columns="hour", values="id", aggfunc="size", fill_value=0)
    piv = piv.reindex(range(7))
    fig, ax = plt.subplots(figsize=(11, 3.4))
    im = ax.imshow(piv.values, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(7)); ax.set_yticklabels(DAYS)
    ax.set_xticks(range(0, 24, 2)); ax.set_xticklabels(range(0, 24, 2))
    ax.set_xlabel("Hour of day (IST)"); ax.set_title("When illegal parking happens — violations by day × hour")
    fig.colorbar(im, ax=ax, label="violations"); fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path


def chart_top_areas(zones, path=OUT / "chart_top_zones.png"):
    z = zones.head(15)[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(z.name.astype(str), z.CIS_100, color="#cc3300")
    ax.set_xlabel("Congestion-Impact Score (0-100)"); ax.set_title("Top-15 illegal-parking enforcement zones")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path


def chart_pareto(pareto, path=OUT / "chart_pareto.png"):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(100 * pareto.zone_frac, 100 * pareto.impact_cov, label="Congestion impact covered", lw=2.2)
    ax.plot(100 * pareto.zone_frac, 100 * pareto.violation_cov, label="Violations covered", lw=1.6, ls="--")
    ax.axvline(10, color="grey", ls=":", lw=1)
    ax.set_xlabel("% of hotspot cells enforced (highest-impact first)")
    ax.set_ylabel("% covered"); ax.set_title("Enforcement ROI — focus beats patrolling everywhere")
    ax.legend(); fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path


def chart_validation(val, path=OUT / "chart_validation.png"):
    if not val.get("available") or "decile_event_counts" not in val:
        return None
    d = val["decile_event_counts"]
    xs = list(range(1, 11)); ys = [d.get(i, 0) for i in xs]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(xs, ys, color="#1f4e96")
    ax.set_xlabel("Congestion-Impact decile of cell (10 = worst parking)")
    ax.set_ylabel("Independent congestion/accident events")
    ax.set_title(f"Validation: real congestion clusters in high-CIS cells "
                 f"(lift {val.get('lift_vs_random','?')}x)")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path


def chart_offender_pareto(pareto, stats, path=OUT / "chart_offenders.png"):
    fig, ax = plt.subplots(figsize=(7, 4.3))
    ax.plot(100 * pareto.veh_frac, 100 * pareto.vio_cov, color="#c0392b", lw=2.3)
    ax.axhline(stats["vio_from_repeat_%"], color="grey", ls=":", lw=1)
    ax.set_xlabel("% of vehicles (worst offenders first)")
    ax.set_ylabel("% of violations")
    ax.set_title(f"Repeat-offender concentration — top 5% of vehicles = "
                 f"{stats['share_top5pct']}% of violations")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path


def chart_severity_mix(df, path=OUT / "chart_severity.png"):
    p = df[df.is_parking]
    top = p.top_violation.value_counts().head(8)[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(top.index.astype(str), top.values, color="#e07b00")
    ax.set_xlabel("violations"); ax.set_title("Dominant parking-violation behaviours")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path
