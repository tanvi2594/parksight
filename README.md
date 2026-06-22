# ParkSight · Parking-Induced Congestion Intelligence

**Gridlock 2.0 — Theme 1: Poor Visibility on Parking-Induced Congestion**

> *How can AI-driven parking intelligence detect illegal-parking hotspots and quantify their
> impact on traffic flow to enable targeted enforcement?*

**ParkSight** turns ~298,000 geo-tagged Bengaluru Traffic Police parking-violation records into a
**validated, deployable enforcement decision-support system**. It detects illegal-parking hotspots,
quantifies each one's impact on traffic flow, forecasts risk, and produces an **optimised,
road-routed patrol plan** — surfacing not just today's hotspots, but **where enforcement is missing**,
**where congestion is emerging**, and **when** to act. Everything is cross-checked against an
*independent* congestion dataset and built on the official partners' infrastructure
(**MapmyIndia / Mappls** maps + routing, **BTP / ASTraM** data).

---

## ⚡ Judge Quickstart (60 seconds)

**▶ Live demo:** https://parksight-56uw7lhwdjegyhwi9vmdmm.streamlit.app
*(Free tier — if it's asleep, give it ~20 s to wake. If a map looks blank, refresh once.)*

**Click these 3 things — they're what sets ParkSight apart:**

1. **Priorities & Deploy → the "optimised vs naive" bar chart.** Same patrol budget, **+13 pp more
   congestion impact covered** — operations-research max-coverage, not just ranking.
2. **Validation tab.** Cross-checked against a **separate, independent** dataset (`astram_event_data.csv`):
   **63%** of independent congestion events fall in our worst-20% parking areas — **3.15× random** —
   then a controlled partial-correlation check, shown honestly.
3. **Command Map → toggle "3D city".** A handful of towers dominate the skyline: visual proof that
   **~7% of the city carries 80% of the impact.**

**Bonus:** type a question into **Ask ParkSight** (e.g. *"deploy Friday 6pm near Koramangala"*) —
plain-English deployment queries, fully offline.

**Data compliance:** all modelling uses **only** the provided `jan to may police
violation_anonymized791b166.csv`; `astram_event_data.csv` is used **only** for validation; maps & routing
are MapmyIndia (Mappls) + OpenStreetMap/OSRM.

---

## 1. Problem

On-street and spillover illegal parking near markets, metro stations and events chokes carriageways
and intersections. Today, enforcement is:
- **Patrol-based and reactive** — officers respond to complaints.
- **Un-visualised** — no heatmap of where violations actually hurt traffic flow.
- **Un-prioritised** — no objective way to allocate limited staff across a city.
- **Un-measured** — no feedback loop to learn whether an action worked.

ParkSight converts raw violation logs into a ranked, validated, deployable plan that closes all four gaps.

---

## 2. The decision loop

```
Detect hotspots → Quantify impact → Forecast risk → Optimise & deploy → Validate & learn  (re-runs monthly)
```

---

## 3. Headline results (Bengaluru, Nov 2023 – Apr 2024)

| Result | Value |
|---|---|
| Violations analysed | **298,445** over 151 days |
| Hotspot cells / enforcement zones | **2,534 / 78** (genuine multi-cell clusters) |
| Cells covering **80%** of impact | **~7% of the city** |
| Forecast — explanatory R² (5-fold CV) | **0.82** |
| Forecast — future hold-out R² (spatial, *unseen* weeks) | **0.88** *(naïve baseline 0.87 — see §7)* |
| Forecast — 80% prediction-interval coverage | **~90%** |
| Hotspot stability (week-to-week pearson) | **0.94** |
| Patrol optimisation uplift (max-coverage vs naive) | **+~13 pp** impact covered, same budget |
| **Validation** — congestion events in worst-20% parking areas | **63% (3.15× random)** |
| Under-enforced high-impact zones found (coverage-gap) | **13** |
| Repeat-offender share of violations | **34%** (worst vehicle 55×) |
| Congestion cost (illustrative range) | **₹0.7 – 3.2 cr / year** |

---

## 4. Features (live Streamlit command center, 9 views)

- **Command Map** — H3 congestion-impact hexagons on **MapmyIndia** tiles (or Streets/Satellite/Light),
  optimised patrol zones, and a **road-following route**; toggle a **3D extruded city**.
- **Ask ParkSight** — natural-language queries (e.g., *"deploy Friday 6 pm near Koramangala"*) →
  plain-English answer + result table + focus map (offline rule-based; no external LLM).
- **Live Ops** — pick the current day & hour → the highest-risk zones to deploy to **this hour**.
- **Priorities & Deploy** — ranked zones, **max-coverage optimisation** (optimised vs naive),
  capacity-constrained **patrol route** (distance/ETA), **ROI** (violations & ₹ averted), ward roll-up,
  CSV/PDF downloads.
- **Forecast** — predicted risk surface (day × hour), CV vs future hold-out vs persistence, confidence bands.
- **Repeat Offenders** — offender-concentration Pareto, top chronic vehicles, deterrence check.
- **Trends** — post-enforcement learning loop (improving vs worsening), monthly time-lapse, emerging watchlist.
- **Coverage & Context** — under-enforced hotspots, enforcement-bias correction, OSM POI (metro/market) context.
- **Validation** — independent-dataset check + controlled (partial-correlation) honesty check.
- **Commander's Briefing PDF** — one-click printable daily brief.

---

## 5. Methodology — Congestion-Impact Score (CIS)

```
CIS = parking-volume × mean severity × chronicity × peak-hour overlap   (scaled 0–100)
```
- **Severity weights (0–1):** how much a violation blocks the carriageway/intersection — main-road &
  road-crossing = 1.0, footpath = 0.4, document offences ≈ 0.05 (expert-set, cross-checked vs congestion).
- **Chronicity:** share of days a cell is active (chronic vs one-off). **Peak overlap:** fraction in rush hours.
- Built with **5-fold out-of-fold (OOF)** target encoding + shrinkage (k=5) toward the global mean → leakage-free.
- **Honest finding:** a controlled check shows CIS tracks congestion mainly via hotspot **density**; the
  severity weighting is an enforcement-**triage** layer (what to act on first), not a congestion predictor.

---

## 6. Models & methods

| Task | Model / method | Notes |
|---|---|---|
| Spatio-temporal **forecast** | **HistGradientBoosting + LightGBM ensemble** on log-intensity | 17 features (below) |
| Forecast **uncertainty** | **Quantile gradient boosting** (P10/P90) | 80% prediction interval per cell |
| Hotspot **clustering** | **DBSCAN** (haversine, eps≈350 m, min_samples=2) | on top-impact H3 cells |
| Patrol **optimisation** | **Submodular max-coverage** (greedy, ≈(1−1/e)) | covers most *unique* impact |
| Severity **calibration** | Non-negative regression vs independent events, blended with priors | transparency, not override |
| Routing | **MapmyIndia** route_adv (OAuth) → OSRM fallback | road-following patrol routes |
| Spatial index | **Uber H3** res 9 (~150 m) | cells, neighbour rings, region rollups |

**Forecast features (17):** lat/lon, hour, day-of-week, cyclic encodings, peak & weekend flags,
cell base-rate, per-cell hour & day profiles, 4-week recency + trend, H3 neighbour-ring density,
region (res-7 / res-6) rates, mean severity, peak share.

---

## 7. Accuracy & validation (evaluated honestly)

- **Forecast — explanatory:** 5-fold CV R² = **0.82**.
- **Forecast — future (true temporal hold-out):** trained on the earliest 16 weeks, scored on the last
  8 **unseen** weeks → **R² 0.88 spatial / 0.72 cell×hour**. A naïve "same as last month" baseline
  already reaches **0.87 spatial** — so hotspots are highly persistent; the model's value is the
  **confidence bands + the operational system**, not beating persistence. (We report this rather than hide it.)
- **Prediction intervals:** 80% bands achieve ~**90%** empirical coverage (conservative).
- **Independent validation:** worst-20% parking areas hold **63%** of independently-reported
  congestion/accident events (**3.15× random**; pearson **0.78**).
- **Controlled check (anti-confounding):** after controlling for raw violation volume, severity adds no
  extra congestion-prediction power → we frame severity as triage, not prediction.
- **Honest null:** an emerging-hotspot *prediction* model scored AUC ≈ 0.52 (cell-level surges are
  unpredictable) — so it was **not** shipped; trend-based monitoring is used instead.

---

## 8. Architecture

```
raw violations CSV (298K) ─► pipeline.py   clean · parse · severity · H3 index
                              ├─► hotspots.py   H3 cells + Congestion-Impact Score ─► DBSCAN zones
                              ├─► forecast.py   HistGB+LightGBM ensemble · temporal hold-out · intervals
                              ├─► analytics.py  offenders · emerging · coverage-gap · cost · routing · OR
                              ├─► validate.py   independent-event validation (+ controlled check)
                              └─► poi.py        OpenStreetMap context
                                       │
                  build_all.py ───────►  outputs/  (csv · geojson · charts · metrics.json)
                                       │
                                  app.py (Streamlit) · routing.py (Mappls/OSRM) · mappls.py (OAuth)
```
- App **boots from committed `outputs/`** (no raw data needed). Config-driven (one block to run on any city).
- Unit-tested (`pytest`). 5-fold OOF encoding prevents target leakage.

---

## 9. Datasets

- **Primary (BTP / ASTraM):** 298,445 geo-tagged violations — location, vehicle no./type, 27 violation
  types, timestamps, officer & device IDs (all **anonymised**). 97% parking-related.
- **Independent (Astram event log):** live congestion / accident / breakdown reports — used **only** for validation.
- **Geospatial:** H3 (res 9) · OpenStreetMap POIs · MapmyIndia maps & routing.

---

## 10. Run it

```bash
pip install -r requirements.txt
streamlit run app.py            # boots from committed outputs/ — no raw data needed
```
Rebuild from scratch (regenerates `outputs/` in ~100 s) — place the data CSVs in the repo root:
```bash
python build_all.py
python -m pytest -q             # unit tests
```
**MapmyIndia:** set `MAPPLS_REST_KEY`, `MAPPLS_CLIENT_ID`, `MAPPLS_CLIENT_SECRET` as env vars /
Streamlit secrets (untracked locally). Without them, the app falls back to OpenStreetMap / OSRM.

---

## 11. Repository structure

| Path | Role |
|---|---|
| `app.py` | Streamlit command center (9 views) |
| `build_all.py` | one-command pipeline → `outputs/` |
| `src/config.py` | city profile, H3 res, severity weights, cost assumptions, partner keys |
| `src/pipeline.py` | load · clean · feature engineering · H3 |
| `src/hotspots.py` | per-cell metrics · Congestion-Impact Score · DBSCAN zones |
| `src/forecast.py` | ensemble model · temporal hold-out · prediction intervals |
| `src/analytics.py` | offenders · emerging · coverage-gap · cost · ward · max-coverage optimisation · routing |
| `src/validate.py` | independent-event validation + controlled check |
| `src/routing.py` · `src/mappls.py` | MapmyIndia/OSRM routing · Mappls OAuth |
| `src/poi.py` · `src/viz.py` | OSM POI context · charts/maps |
| `tests/test_pipeline.py` | unit tests |

---

## 12. Partners & stack
**Partners:** MapmyIndia (Mappls) maps + routing · Bengaluru Traffic Police (ASTraM) data.
**Stack:** Python · pandas · NumPy · scikit-learn · LightGBM · Uber H3 · Plotly · pydeck · Streamlit ·
OSRM · OpenStreetMap.

---

## 13. Limitations (we surface our own holes)
- We **proxy** congestion (no live flow data); validated against an independent congestion log.
- Enforcement data = where patrols looked (selection bias) — surfaced and corrected.
- Temporal pattern = detection times (officer shifts) — framed as detection-risk, not raw demand.
- Validation is associational, not causal (controlled check shown).
- ₹ cost & enforcement effectiveness are illustrative ranges; forecast ≈ persistence + a small edge.
- One city, ~5 months; pipeline is config-driven to generalise.

---

## 14. Roadmap
Live data ingestion + auto-refresh · fuse real-time speed/probe data to calibrate impact causally ·
before/after impact measurement (closed learning loop) · ANPR/camera capture at top zones · multi-city rollout.
