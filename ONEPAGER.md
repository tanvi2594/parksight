# ParkSight — One-Page Summary
### Parking-Induced Congestion Intelligence · Gridlock 2.0 · Theme 1

> **Enforce ~7% of the city, address 80% of the parking-induced congestion.**

**What it is —** an AI decision-support system that turns the Bengaluru Traffic Police's own
**298,445 parking-violation records** into a *validated, deployable* enforcement plan: it detects
illegal-parking hotspots, **quantifies each one's impact on traffic flow**, forecasts risk, and produces
an **optimised, road-routed patrol plan** — surfacing not just today's hotspots, but **where enforcement is
missing, where congestion is emerging, and when to act.** Live, interactive, running on **MapmyIndia (Mappls)**
maps + routing.

---

### Headline results
| Metric | Value |
|---|---|
| Violations analysed | **298,445** over 151 days |
| Hotspot cells → enforcement zones | **2,534 → 78** |
| Concentration | **~7% of the city = 80% of impact** |
| Patrol optimisation (max-coverage vs naive) | **+~13 pp** impact covered, *same budget* |
| Forecast (true temporal hold-out, unseen weeks) | **R² 0.88** spatial · 80% bands at **90%** coverage |
| Forecast vs persistence (location×hour) | **0.72 vs 0.69** + hours + uncertainty + 278 emerging cells |
| **Independent validation** (separate dataset) | **63%** of congestion in worst-20% areas · **3.15× random** |
| Coverage-gap (under-enforced high-impact zones) | **13** |
| Repeat-offender share | **34%** of violations (worst vehicle 55×) |

---

### Why it stands out
- **Quantifies impact, not counts** — a severity-weighted Congestion-Impact Score (CIS).
- **Operations-research optimisation** — submodular max-coverage patrol placement (≈(1−1/e)), not just ranking.
- **The non-obvious intelligence** — *coverage-gap* (where enforcement is missing) + *emerging-hotspot* watch.
- **Independently validated** against a separate dataset, with a controlled partial-correlation honesty check.
- **Deployable today** — runs on the police's own data + MapmyIndia's own maps; honest about its limitations.

### The 9-view live command center
Command Map (impact hexagons + 3D city on Mappls) · Ask ParkSight (plain-English queries) · Live Ops
(deploy this hour) · Priorities & Deploy (optimise + road route + ROI) · Forecast (confidence bands) ·
Repeat Offenders · Trends (post-enforcement learning) · Coverage & Context · Independent Validation ·
one-click PDF Commander's Briefing.

---

### Data & compliance
- **All modelling** uses **only** the provided Theme-1 file `jan to may police violation_anonymized791b166.csv`.
- `astram_event_data.csv` (provided event log) is used **only** for independent validation — never for training.
- **No external training data.** Maps & routing = MapmyIndia (Mappls) + OpenStreetMap/OSRM (infrastructure).

### Stack
Python · pandas · scikit-learn · LightGBM · Uber H3 · Plotly · pydeck · Streamlit · MapmyIndia (Mappls) · OSRM.

---

**▶ Live demo:** https://parksight-56uw7lhwdjegyhwi9vmdmm.streamlit.app
**Repository:** https://github.com/tanvi2594/parksight
