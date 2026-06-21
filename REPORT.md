# ParkSight · Solution Report
### Theme 1: Poor Visibility on Parking-Induced Congestion

---

## 1. The problem
On-street and spillover illegal parking near commercial areas, metro stations and events
chokes carriageways and intersections. Today enforcement is **patrol-based and reactive**,
there is **no heatmap of violations vs. congestion impact**, and it is **hard to prioritise**
where to deploy limited staff.

## 2. Our solution in one line
**ParkSight converts raw parking-violation logs into a ranked, validated, forecastable
enforcement plan · showing *where* illegal parking hurts traffic most, *how much*, and
*when* to act.**

## 3. Data
- **Primary:** 298,445 geo-tagged police parking-violation records, Bengaluru,
  Nov 2023–Apr 2024 (169 junctions, 54 stations, 27 violation types, 97% parking).
- **Validation (independent):** Astram event log · live congestion/accident/breakdown reports.

## 4. Method (5 steps)
1. **Severity model** · each violation type is weighted 0–1 by how much it blocks the
   carriageway/intersection (main-road & road-crossing parking = 1.0; footpath = 0.4;
   document offences ≈ 0.05). This is what converts "a violation" into "traffic impact".
2. **Hotspot detection** · violations are binned into **H3 ~150 m cells**; adjacent
   high-impact cells are merged into **enforcement zones** with DBSCAN.
3. **Congestion-Impact Score (CIS)** =
   `parking volume × mean severity × chronicity × peak-hour overlap`, scaled 0–100.
4. **Risk forecasting** · a gradient-boosted model predicts expected violations for every
   **(location × day-of-week × hour)** slot → proactive patrol windows.
5. **Optimisation** · Pareto prioritisation + a capacity-constrained patrol plan that
   maximises impact addressed per patrol unit.

## 5. Results
- **2,534** hotspot cells, **248** enforcement zones; #1 = **Cottonpet Circle** (a real
  known chokepoint · found with no labels).
- **Focus pays off:** the worst **~7%** of cells account for **80%** of all parking-induced
  congestion impact; the top **10%** cover **86%**.
- **Forecastable:** risk-model CV **R² = 0.70**; hotspot locations are **94%** stable
  half-to-half, so schedules hold up week to week.
- **Repeat offenders:** **34%** of all violations come from vehicles caught ≥2×; the worst
  single vehicle was caught **55×** → targeted notices beat blanket enforcement.
- **Emerging hotspots:** **278** areas with sharply rising violations flagged early.
- **Coverage gap:** **13** high-impact zones identified as under-enforced (severe impact,
  very few enforcement days) · direct patrol-frequency recommendations.

## 5b. Advanced, interactive capabilities (dashboard)
- **Deploy & Simulate** · a live slider allocates *N* patrol units to the highest-impact zones
  and instantly recomputes congestion-impact coverage and violations addressed.
- **Repeat-offender intelligence**, **emerging-hotspot early-warning**, and **enforcement
  coverage-gap** views, each with maps/Pareto charts and ranked action tables.

## 6. Why judges should trust it · independent validation
We cross-checked the Impact Score against a **completely separate** congestion/accident log:
- Correlation of CIS vs independent congestion density: **0.78** (neighbourhood level).
- **63%** of all independently-reported congestion/accident events fall inside the
  **worst-20%** parking areas we flagged · **3.15× more than random**.

➡️ The score is not a heuristic guess; it tracks **real traffic breakdowns**.

## 7. Operational impact
- A live **heatmap** of parking-induced congestion (the missing visibility).
- A **ranked zone list + patrol plan** → targeted, defensible enforcement.
- **Proactive scheduling** → shift from reactive patrols to data-driven deployment.
- **ROI story:** cover 80% of the problem by enforcing ~7% of the city.

## 8. Roadmap (productionisation)
- Live ingestion + auto-refreshing dashboard; push patrol plans to the field app.
- Fuse real-time speed/probe data to calibrate severity weights causally.
- Before/after impact measurement to create the missing **post-enforcement learning loop**.
- Camera/ANPR feeds for automatic violation capture at top zones.

## 9. Tech stack
Python · pandas · H3 · scikit-learn (HistGradientBoosting, DBSCAN) · folium · Streamlit.
Reproducible: `pip install -r requirements.txt && python build_all.py && streamlit run app.py`.
