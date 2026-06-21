"""Run the full Parking-Induced Congestion Intelligence pipeline and write every
artifact (tables, maps, charts, metrics) into ./outputs. Run once before the app:
    python build_all.py
"""
import json
import time
import numpy as np
import pandas as pd

from src.config import OUT
from src.pipeline import load_clean
from src.hotspots import cell_table, cluster_zones
from src.forecast import (build_slot_panel, train_risk_model, temporal_stability,
                          temporal_holdout_forecast, recommend_schedule)
from src.optimize import pareto_coverage, roi_headline, allocate_patrols
from src.validate import validate_against_events, load_events, topzone_precision
from src.analytics import (repeat_offenders, emerging_hotspots, coverage_gap, congestion_cost,
                           zone_trends, deterrence, ward_rollup, calibrate_severity,
                           recompute_severity, demand_adjusted, emergence_prediction)
from src.hotspots import _area_name
from src.poi import fetch_poi, context_stats
from src import viz


def main():
    t0 = time.time()
    print("[1/7] loading + cleaning ...")
    df = load_clean(force=True)
    print(f"      {len(df):,} clean rows | {df.date.nunique()} days | "
          f"{100*df.is_parking.mean():.1f}% parking")

    print("[2/7] calibrating severity from independent events + building cells ...")
    ev0 = load_events()
    sev_weights, sev_comp = calibrate_severity(df, ev0)
    if len(sev_comp):
        df = recompute_severity(df, sev_weights)
        sev_comp.to_csv(OUT / "severity_calibrated.csv", index=False)
    cells = cell_table(df)
    cells.to_csv(OUT / "cells.csv", index=False)

    print("[3/7] clustering enforcement zones + ward roll-up + hex map ...")
    zones = cluster_zones(cells)
    zones.to_csv(OUT / "zones.csv", index=False)
    ward_rollup(cells, zones).to_csv(OUT / "ward_rollup.csv", index=False)
    with open(OUT / "cells_hex.geojson", "w") as f:
        json.dump(viz.hex_geojson(cells), f)

    print("[4/7] training spatio-temporal risk model ...")
    slot = build_slot_panel(df)
    model, fc_metrics, slot_pred = train_risk_model(slot)
    stab = temporal_stability(df)
    holdout = temporal_holdout_forecast(df)
    schedule = recommend_schedule(slot_pred, top=300)
    schedule.to_csv(OUT / "schedule.csv", index=False)
    slot_pred.to_parquet(OUT / "slot_risk.parquet", index=False)

    print("[5/7] enforcement optimisation + ROI ...")
    pareto = pareto_coverage(cells); pareto.to_csv(OUT / "pareto.csv", index=False)
    roi = roi_headline(pareto)
    plan = allocate_patrols(zones, n_patrols=15); plan.to_csv(OUT / "patrol_plan.csv", index=False)

    print("[6/8] enforcement analytics (offenders / emerging / coverage-gap) ...")
    off_stats, off_pareto, off_top = repeat_offenders(df)
    off_top.to_csv(OUT / "offenders_top.csv", index=False)
    off_pareto.iloc[:: max(1, len(off_pareto) // 2000)].to_csv(OUT / "offenders_pareto.csv", index=False)
    emerging = emerging_hotspots(df, cells); emerging.to_csv(OUT / "emerging.csv", index=False)
    gap_stats, under, gap_map = coverage_gap(df, cells); under.to_csv(OUT / "coverage_gap.csv", index=False)
    cost_stats, cost_map = congestion_cost(cells, df.date.nunique())
    cost_map.to_csv(OUT / "cost_map.csv", index=False)
    # #2 enforcement-bias corrected impact
    dadj = demand_adjusted(cells, df); dadj.to_csv(OUT / "demand_adjusted.csv", index=False)
    # #5 drill-down: per-area hour profile + vehicle mix (top areas)
    dp = df[df.is_parking].copy(); dp["area"] = dp.location.map(_area_name)
    top_areas = dp.area.value_counts().head(80).index
    sub = dp[dp.area.isin(top_areas)]
    sub.groupby(["area", "hour"]).size().rename("n").reset_index().to_csv(OUT / "area_hourly.csv", index=False)
    sub.groupby(["area", "vehicle_type"]).size().rename("n").reset_index().to_csv(OUT / "area_vehicles.csv", index=False)
    trend_stats, trends, city_trend = zone_trends(df, cells)
    trends.to_csv(OUT / "zone_trends.csv", index=False); city_trend.to_csv(OUT / "city_trend.csv", index=False)
    det_stats = deterrence(df)
    # monthly per-cell counts for the time-lapse animation
    mc = df[df.is_parking].copy(); mc["month"] = mc.dt.dt.to_period("M").astype(str)
    (mc.groupby(["h3", "month"]).size().rename("n").reset_index()
       .merge(cells[["h3", "lat", "lon", "area", "CIS"]], on="h3")
       .to_csv(OUT / "cells_monthly.csv", index=False))

    print("[7/9] POI / transit context (OpenStreetMap) ...")
    poi = fetch_poi()
    poi_stats, poi_zones = context_stats(zones, poi)
    if len(poi): poi.to_csv(OUT / "poi.csv", index=False)
    poi_zones.to_csv(OUT / "poi_zones.csv", index=False)

    print("[8/9] cross-dataset validation vs independent events ...")
    val = validate_against_events(cells)
    val["topzone_precision"] = topzone_precision(zones)
    events = load_events()

    print("[9/9] rendering maps + charts ...")
    viz.hotspot_map(cells, zones, events[events.event_cause.isin(["congestion", "accident"])]
                    if len(events) else None)
    viz.chart_hour_dow(df); viz.chart_top_areas(zones); viz.chart_pareto(pareto)
    viz.chart_validation(val); viz.chart_severity_mix(df)
    viz.chart_offender_pareto(off_pareto, off_stats)

    metrics = {
        "rows_total": int(len(df)),
        "days": int(df.date.nunique()),
        "parking_share_pct": round(100 * df.is_parking.mean(), 1),
        "n_cells": int(len(cells)),
        "n_zones": int(len(zones)),
        "n_chronic_cells": int((cells["class"] == "Chronic").sum()),
        "forecast": fc_metrics,
        "stability": stab,
        "roi": roi,
        "offenders": off_stats,
        "emerging": {"n_emerging": int(len(emerging)),
                     "top_growth_x": float(emerging.growth_x.iloc[0]) if len(emerging) else None,
                     "top_area": (emerging.area.iloc[0] if len(emerging) else None)},
        "coverage": gap_stats,
        "cost": cost_stats,
        "severity_calibrated": bool(len(sev_comp)),
        "pi_coverage_80": fc_metrics.get("pi_coverage_80"),
        "trends": trend_stats,
        "deterrence": det_stats,
        "poi": poi_stats,
        "holdout": holdout,
        "validation": val,
        "top_zone": (zones.iloc[0][["name", "CIS_100", "n_parking", "top_violation",
                                    "police_station"]].to_dict() if len(zones) else {}),
        "runtime_sec": round(time.time() - t0, 1),
    }
    with open(OUT / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print("\n==================  HEADLINE RESULTS  ==================")
    print(f"  Hotspot cells .............. {metrics['n_cells']:,}")
    print(f"  Enforcement zones .......... {metrics['n_zones']}")
    print(f"  Chronic cells .............. {metrics['n_chronic_cells']:,}")
    print(f"  Risk-model CV R^2 .......... {fc_metrics['cv_r2']}")
    print(f"  FUTURE hold-out R^2 ........ {holdout['holdout_r2_cellhour']} cell x hour "
          f"(train {holdout['train_weeks']}w -> predict {holdout['test_weeks']}w; "
          f"{holdout['lift_vs_persistence']}x vs persistence)")
    print(f"  Spatial stability pearson .. {stab['spatial_pearson']} (chronic spots persist)")
    print(f"  Post-enforce trend ......... {trend_stats['improving']} improving / "
          f"{trend_stats['worsening']} worsening hotspots")
    if poi_stats.get('available'):
        print(f"  POI context ................ {poi_stats['pct_top_near_poi']}% of top zones within "
              f"{poi_stats['radius_m']}m of metro/market/mall ({poi_stats['n_poi']} POIs)")
    print(f"  Top 10% cells cover ........ {roi['impact_covered_top10pct_zones']}% of impact")
    print(f"  Zones for 80% impact ....... {roi['zones_for_80pct_impact']} of {roi['total_cells']:,}")
    print(f"  Repeat offenders ........... {off_stats['vio_from_repeat_%']}% of violations from "
          f"repeat vehicles; worst vehicle caught {off_stats['max_by_one_vehicle']}x")
    print(f"  Emerging hotspots .......... {len(emerging)} rising zones "
          f"(top growth {emerging.growth_x.iloc[0] if len(emerging) else 'NA'}x)")
    print(f"  Under-enforced hotspots .... {gap_stats['n_under_enforced']} high-impact zones with weak patrol effort")
    print(f"  Congestion cost ............ Rs {cost_stats['annual_cost_cr']} cr/yr "
          f"({cost_stats['top10pct_cost_share_%']}% in top 10% cells)")
    if val.get("available"):
        print(f"  Validation (neighbourhood) . pearson {val.get('neighbourhood_pearson_res6','?')}, "
              f"lift {val.get('neighbourhood_lift','?')}x "
              f"({val.get('neighbourhood_events_top20pct_%','?')}% of real congestion in worst-20% areas)")
    print(f"  Runtime .................... {metrics['runtime_sec']}s")
    print("  Artifacts -> ./outputs/  (cells, zones, schedule, patrol_plan, maps, charts, metrics)")
    print("=======================================================")


if __name__ == "__main__":
    main()
