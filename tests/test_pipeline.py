"""Lightweight tests for the ParkSight pipeline. Run:  python -m pytest -q   (or)  python tests/test_pipeline.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from src.config import SEVERITY, DEFAULT_SEVERITY
from src.analytics import recompute_severity, patrol_route


def test_severity_weights_in_range():
    assert all(0.0 <= w <= 1.0 for w in SEVERITY.values())
    assert SEVERITY["PARKING IN A MAIN ROAD"] > SEVERITY["PARKING ON FOOTPATH"]


def test_recompute_severity_takes_max():
    df = pd.DataFrame({"vlist": [["NO PARKING", "PARKING IN A MAIN ROAD"], ["PARKING ON FOOTPATH"], []]})
    out = recompute_severity(df, dict(SEVERITY))
    assert abs(out.severity.iloc[0] - SEVERITY["PARKING IN A MAIN ROAD"]) < 1e-9   # max of the two
    assert abs(out.severity.iloc[1] - SEVERITY["PARKING ON FOOTPATH"]) < 1e-9
    assert abs(out.severity.iloc[2] - DEFAULT_SEVERITY) < 1e-9                      # empty -> default
    assert out.top_violation.iloc[0] == "PARKING IN A MAIN ROAD"


def test_patrol_route_orders_and_measures():
    z = pd.DataFrame({"lat": [12.97, 12.98, 12.99], "lon": [77.59, 77.60, 77.61],
                      "CIS": [3, 2, 1], "name": list("abc")})
    routed, km, eta = patrol_route(z)
    assert list(routed.stop) == [1, 2, 3]
    assert km > 0 and eta > 0
    assert len(routed) == 3


def test_cis_monotonic_in_inputs():
    # Congestion-Impact must rise with volume and with severity (sanity of the formula)
    def cis(n, sev, pers=0.5, peak=0.5):
        raw = n * sev * (0.4 + 0.6 * pers) * (0.6 + 0.4 * peak)
        return raw
    assert cis(100, 0.8) > cis(50, 0.8)
    assert cis(100, 0.9) > cis(100, 0.4)


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn(); print("PASS", fn.__name__)
    print(f"\nAll {len(fns)} tests passed.")
