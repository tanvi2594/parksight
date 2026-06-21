"""ParkSight pitch deck — detailed, professional, with screenshot placeholders + speaker notes."""
import json
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parent
M = json.load(open(ROOT / "outputs" / "metrics.json"))
f, ho, v = M["forecast"], M["holdout"], M["validation"]
cost, o, roi = M["cost"], M["offenders"], M["roi"]
cov = M.get("coverage", {}); emg = M.get("emerging", {})

NAVY = RGBColor(0x0F, 0x1D, 0x35); NAVY2 = RGBColor(0x24, 0x3A, 0x60)
BLUE = RGBColor(0x25, 0x63, 0xEB); SKY = RGBColor(0x9D, 0xC2, 0xFF)
INK = RGBColor(0x1F, 0x29, 0x37); MUTE = RGBColor(0x6B, 0x7A, 0x90)
WHITE = RGBColor(0xFF, 0xFF, 0xFF); GREEN = RGBColor(0x05, 0x96, 0x69)
RED = RGBColor(0xDC, 0x26, 0x26); VIO = RGBColor(0x7C, 0x3A, 0xED); AMBER = RGBColor(0xD9, 0x77, 0x06)
LIGHT = RGBColor(0xF4, 0xF7, 0xFB); LINE = RGBColor(0xE3, 0xE8, 0xF0)
PHF = RGBColor(0xEC, 0xF1, 0xF8); PHB = RGBColor(0xB6, 0xC6, 0xDE)

prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]; SW, SH = prs.slide_width, prs.slide_height
_page = [0]


def _bg(s, c):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH); r.fill.solid()
    r.fill.fore_color.rgb = c; r.line.fill.background(); r.shadow.inherit = False
    s.shapes._spTree.remove(r._element); s.shapes._spTree.insert(2, r._element)


def box(s, x, y, w, h):
    tf = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True; return tf


def txt(tf, t, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, space=5, mono=False, first=False):
    p = tf.paragraphs[0] if (first or (len(tf.paragraphs) == 1 and not tf.paragraphs[0].runs)) else tf.add_paragraph()
    p.alignment = align; p.space_after = Pt(space)
    r = p.add_run(); r.text = str(t)
    r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color
    r.font.name = "Consolas" if mono else "Inter"
    return p


def rect(s, x, y, w, h, c, shape=MSO_SHAPE.RECTANGLE, line=None, lw=1.0):
    sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = c; sh.shadow.inherit = False
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(lw)
    return sh


def note(s, t):
    s.notes_slide.notes_text_frame.text = t


def footer(s):
    _page[0] += 1
    rect(s, 0, 7.18, 13.333, 0.012, LINE)
    txt(box(s, 0.6, 7.2, 9, 0.3), "ParkSight  ·  Gridlock 2.0  ·  Theme 1 — Parking-Induced Congestion", 9, MUTE)
    txt(box(s, 12.2, 7.2, 0.7, 0.3), str(_page[0]), 9, MUTE, align=PP_ALIGN.RIGHT)


def content(kicker, title, sub=None):
    s = prs.slides.add_slide(BLANK); _bg(s, WHITE)
    rect(s, 0.6, 0.52, 0.16, 0.62, BLUE)
    txt(box(s, 0.95, 0.48, 11.6, 0.34), kicker, 12, BLUE, True)
    txt(box(s, 0.95, 0.82, 11.7, 0.66), title, 25, INK, True)
    rect(s, 0.95, 1.5, 11.45, 0.02, LINE)
    if sub:
        txt(box(s, 0.95, 1.56, 11.6, 0.4), sub, 12.5, MUTE)
    footer(s)
    return s


def divider(num, kicker, title):
    s = prs.slides.add_slide(BLANK); _bg(s, NAVY)
    txt(box(s, 0.9, 1.7, 5, 1.8), num, 96, NAVY2, True)
    rect(s, 0.98, 3.95, 2.2, 0.06, BLUE)
    txt(box(s, 0.98, 4.15, 11, 0.4), kicker, 13, SKY, True)
    txt(box(s, 0.98, 4.55, 11.5, 1.0), title, 30, WHITE, True)
    return s


def card(s, x, y, w, val, label, color=BLUE, h=1.55):
    rect(s, x, y, w, h, LIGHT, MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE, lw=1)
    rect(s, x + 0.12, y + 0.12, w - 0.24, 0.08, color)
    tf = box(s, x + 0.18, y + 0.28, w - 0.32, h - 0.36)
    txt(tf, val, 21, color, True, first=True); txt(tf, label, 10.5, MUTE, space=0)


def bullets(s, x, y, w, h, items, size=15, space=8):
    tf = box(s, x, y, w, h)
    for i, t in enumerate(items):
        if t == "":
            txt(tf, "", 6, MUTE, space=2, first=(i == 0)); continue
        txt(tf, t, size, INK if not t.startswith("›") else MUTE, bold=t.endswith(":"), space=space, first=(i == 0))
    return tf


def ph(s, x, y, w, h, label):
    r = rect(s, x, y, w, h, PHF, MSO_SHAPE.ROUNDED_RECTANGLE, line=PHB, lw=1.25)
    r.text_frame.word_wrap = True; r.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    txt(r.text_frame, "🖼  Screenshot: " + label, 12.5, MUTE, True, PP_ALIGN.CENTER, space=0, first=True)


def table(s, x, y, w, data, col_w, row_h=0.34, head_h=0.4, fs=11.5):
    rows, cols = len(data), len(data[0]); h = head_h + row_h * (rows - 1)
    gt = s.shapes.add_table(rows, cols, Inches(x), Inches(y), Inches(w), Inches(h)).table
    gt.first_row = False; gt.horz_banding = False
    for ci in range(cols):
        gt.columns[ci].width = Inches(col_w[ci])
    for ri, row in enumerate(data):
        gt.rows[ri].height = Inches(head_h if ri == 0 else row_h)
        for ci, val in enumerate(row):
            cell = gt.cell(ri, ci); cell.margin_left = Inches(0.1); cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03); cell.vertical_anchor = MSO_ANCHOR.MIDDLE; cell.text = str(val)
            p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
            rn = p.runs[0]; rn.font.name = "Inter"; rn.font.size = Pt(fs)
            if ri == 0:
                cell.fill.solid(); cell.fill.fore_color.rgb = NAVY; rn.font.color.rgb = WHITE; rn.font.bold = True
            else:
                cell.fill.solid(); cell.fill.fore_color.rgb = WHITE if ri % 2 else LIGHT; rn.font.color.rgb = INK
                if ci == 1:
                    rn.font.bold = True; rn.font.color.rgb = BLUE
    return gt


# ════════════════════════════ COVER
s = prs.slides.add_slide(BLANK); _bg(s, NAVY)
rect(s, 0, 0, 0.22, 7.5, BLUE); rect(s, 0.9, 3.18, 3.4, 0.06, BLUE)
txt(box(s, 0.85, 1.9, 11.5, 1.1), "ParkSight", 56, WHITE, True)
txt(box(s, 0.9, 3.35, 11.6, 0.7), "Parking-Induced Congestion Intelligence", 23, SKY)
txt(box(s, 0.9, 4.25, 11.4, 0.9),
    "An AI decision-support system that detects illegal-parking hotspots, quantifies their impact on "
    "traffic flow, forecasts risk, and produces an optimised, road-routed enforcement plan.", 14,
    RGBColor(0xC7, 0xD4, 0xEA))
txt(box(s, 0.9, 6.45, 11.6, 0.4),
    "Gridlock 2.0  ·  Theme 1  ·  Built on Bengaluru Traffic Police (ASTraM) data + MapmyIndia (Mappls) maps",
    11.5, RGBColor(0x8A, 0xA0, 0xC0))
note(s, "Opening line: 'Illegal parking is one of the most fixable causes of urban congestion — yet "
        "enforcement today is blind and reactive. ParkSight turns the traffic police's own 300,000 violation "
        "records into a live, validated, deployable plan that says exactly where, when, and how to enforce.' "
        "Stress: built on the partners' real data and MapmyIndia maps — deployable, not a toy.")

# ════════════════════════════ 01
divider("01", "PROBLEM & APPROACH", "Enforcement is blind, reactive, un-prioritised")
note(prs.slides[-1], "Section 1 sets up the operational pain and our framing: turn logs into a decision loop.")

s = content("THE PROBLEM", "Four gaps in parking enforcement today",
            "On-street & spillover illegal parking near markets, metros and events chokes carriageways.")
for (title, body, col), x in zip(
        [("Reactive", "Patrol-based; officers respond to complaints, not data.", RED),
         ("Invisible", "No heatmap of where violations actually hurt traffic flow.", AMBER),
         ("Un-prioritised", "No objective way to allocate limited staff city-wide.", VIO),
         ("Un-measured", "No feedback loop to learn whether an action worked.", BLUE)],
        [0.95, 3.95, 6.95, 9.95]):
    rect(s, x, 2.2, 2.85, 2.7, LIGHT, MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE, lw=1)
    rect(s, x + 0.18, 2.42, 0.5, 0.1, col)
    tf = box(s, x + 0.18, 2.62, 2.55, 2.2)
    txt(tf, title, 16, INK, True, first=True); txt(tf, body, 12, MUTE, space=0)
txt(box(s, 0.95, 5.3, 11.6, 0.7),
    "Goal: convert raw violation logs into a ranked, validated, deployable enforcement plan.", 15, INK, True)
note(s, "Walk the four cards left-to-right. Land the goal line: we're not just visualising data — we're "
        "producing an ACTION plan a DCP can deploy tomorrow. These four gaps map to our five-stage loop.")

s = content("THE SOLUTION", "A closed, end-to-end decision loop")
x = 0.95
for i, t in enumerate(["Detect\nhotspots", "Quantify\nimpact", "Forecast\nrisk", "Optimise\n& deploy", "Validate\n& learn"]):
    c = rect(s, x, 2.7, 2.55, 1.4, BLUE if i % 2 == 0 else NAVY, MSO_SHAPE.CHEVRON)
    c.text_frame.word_wrap = True; txt(c.text_frame, t, 14, WHITE, True, PP_ALIGN.CENTER, first=True); x += 2.3
bullets(s, 0.95, 4.7, 11.7, 1.8, [
    "Each stage is a working module in a live Streamlit command center (9 interactive views).",
    "The loop re-runs monthly, so any enforcement action can be measured — the post-event learning the brief asks for.",
], size=15, space=9)
note(s, "Emphasise CLOSED loop — most teams stop at 'detect/visualise'. We forecast, optimise deployment, "
        "validate against independent data, and re-measure monthly. That last step is exactly the 'post-event "
        "learning system' the problem statement asks for.")

s = content("ARCHITECTURE", "Reproducible pipeline → artifacts → live app")
rect(s, 0.95, 1.8, 11.45, 3.55, LIGHT, MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE, lw=1)
mono = box(s, 1.2, 2.0, 11.0, 3.2)
for i, t in enumerate([
    "raw violations CSV (298K) ─► pipeline.py    clean · parse · severity · H3 index",
    "                             ├─► hotspots.py   H3 cells + Congestion-Impact Score ─► DBSCAN zones",
    "                             ├─► forecast.py   HistGB + LightGBM ensemble · hold-out · intervals",
    "                             ├─► analytics.py  offenders · emerging · coverage-gap · cost · OR · routing",
    "                             ├─► validate.py   independent-event validation (+ controlled check)",
    "                             └─► poi.py        OpenStreetMap context",
    "                                       │",
    "          build_all.py ───────────────►  outputs/  (csv · geojson · charts · metrics.json)",
    "                                       │",
    "                                  app.py (Streamlit) · routing.py (Mappls/OSRM) · mappls.py (OAuth)",
]):
    txt(mono, t, 11, INK, mono=True, space=2, first=(i == 0))
bullets(s, 0.95, 5.55, 11.7, 1.2, [
    "Boots from committed artifacts (no raw data needed) · 5-fold out-of-fold encoding prevents leakage · "
    "config-driven for any city · unit-tested (pytest).",
], size=12.5, space=5)
note(s, "One-liner: 'It's not a notebook — it's an engineered, reproducible system.' Mention leakage-free OOF "
        "encoding and unit tests if a technical judge asks. The app runs from pre-computed artifacts so the "
        "demo never needs the 109 MB raw file.")

# ════════════════════════════ 02
divider("02", "DATA & METHODOLOGY", "Real partner data, a transparent impact score")
note(prs.slides[-1], "Section 2: the data we used and how we turn it into a defensible impact metric.")

s = content("DATA", "Real partner datasets — no synthetic scenarios")
card(s, 0.95, 1.9, 3.7, "298,445", "police parking violations", BLUE)
card(s, 4.85, 1.9, 3.7, "151 days", "Nov 2023 – Apr 2024", GREEN)
card(s, 8.75, 1.9, 3.6, "169 / 54", "junctions / stations", VIO)
bullets(s, 0.95, 3.75, 11.7, 2.8, [
    "Primary — Bengaluru Traffic Police / ASTraM: geo-tagged violations (location, vehicle no./type, "
    "27 violation types, timestamps, officer & device IDs — all anonymised). 97% parking-related.",
    "Independent — Astram event log: live congestion / accident / breakdown reports — used ONLY for validation.",
    "Geospatial — Uber H3 hex index (res 9, ≈150 m) · OpenStreetMap POIs · MapmyIndia maps & routing.",
], size=14.5, space=11)
note(s, "Stress 'real partner data, not simulated'. The second dataset is independent — we never train on it, "
        "we only validate against it, which is what makes our validation credible.")

s = content("METHODOLOGY", "Congestion-Impact Score (CIS)")
rect(s, 0.95, 1.85, 11.45, 0.9, NAVY, MSO_SHAPE.ROUNDED_RECTANGLE)
txt(box(s, 1.1, 2.02, 11.1, 0.6),
    "CIS  =  parking-volume  ×  mean severity  ×  chronicity  ×  peak-hour overlap     (scaled 0–100)",
    16, WHITE, True, PP_ALIGN.CENTER)
table(s, 0.95, 3.0, 11.45, [
    ["Component", "What it captures", "Source"],
    ["Volume", "How many violations occur in the cell", "counts per H3 cell"],
    ["Severity (0–1)", "How much the violation blocks traffic", "expert weights, cross-checked"],
    ["Chronicity", "Persistent vs one-off problem", "share of active days"],
    ["Peak overlap", "Concentration in rush hours", "fraction in peak windows"],
], col_w=[2.5, 6.35, 2.6], fs=12)
bullets(s, 0.95, 5.55, 11.7, 1.2, [
    "Leakage-free: 5-fold out-of-fold encoding + shrinkage (k=5). Honest: a controlled check shows CIS tracks "
    "congestion mainly via DENSITY — severity is an enforcement-triage layer, not a congestion predictor.",
], size=12.5, space=5)
note(s, "The CIS is the heart of the project: it turns 'a violation' into 'traffic impact'. Severity weights "
        "(main-road parking = 1.0, footpath = 0.4, document offences ≈ 0). Be honest about the controlled check "
        "— it shows intellectual rigour and pre-empts the 'isn't this just counting?' question.")

s = content("DETECTION", "Hotspots → enforcement zones (H3 + DBSCAN)")
bullets(s, 0.95, 1.85, 5.25, 4.5, [
    "Spatial index: Uber H3 resolution 9 (≈150 m hexagons).",
    "Aggregate each violation to its cell; compute CIS per cell.",
    "Cluster adjacent high-impact cells into ZONES with DBSCAN "
    "(haversine, eps≈350 m, min_samples=2 → genuine clusters).",
    "",
    f"{M['n_cells']:,} hotspot cells → {M['n_zones']} enforcement zones.",
    "~7% of cells hold 80% of total impact.",
    "Top zones are real chokepoints — Cottonpet, City Market, Chickpet — found with zero manual labels.",
], size=14, space=8)
ph(s, 6.5, 1.85, 5.9, 4.55, "Command Map — impact hexagons + zones (MapmyIndia)")
note(s, "Point to the map. The model independently rediscovers Cottonpet / City Market as #1 hotspots — "
        "places any Bengaluru traffic officer instantly recognises. That face-validity builds trust fast.")

# ════════════════════════════ 03
divider("03", "MODELS & ACCURACY", "Forecasting · optimisation · validation")
note(prs.slides[-1], "Section 3 is for the technical judges: the models, the numbers, evaluated honestly.")

s = content("MODEL · FORECASTING", "Spatio-temporal risk model")
bullets(s, 0.95, 1.8, 6.05, 4.6, [
    "Target: expected violations per (cell × day-of-week × hour).",
    "Model: ENSEMBLE — HistGradientBoosting + LightGBM (averaged), on log-intensity.",
    "Features (17): lat/lon, hour, day, cyclic encodings, peak/weekend flags, cell base-rate, per-cell "
    "hour & day profiles, 4-week recency + trend, H3 neighbour-ring density, region (res-7/6) rates, severity.",
    "Uncertainty: quantile gradient boosting → 80% prediction interval per cell.",
    "Validation: true TEMPORAL hold-out (train 16 wks → score 8 unseen wks).",
], size=13.5, space=8)
table(s, 7.25, 1.85, 5.15, [
    ["Metric", "Value"],
    ["Explanatory R² (5-fold CV)", f["cv_r2"]],
    ["Future R² · where (spatial)", ho["holdout_r2_spatial"]],
    ["Future R² · where + hour", ho["holdout_r2_cellhour"]],
    ["Naïve persistence (spatial)", ho["persistence_r2_spatial"]],
    ["80% interval coverage", f"{int(100*M.get('pi_coverage_80',0))}%"],
], col_w=[3.55, 1.6], fs=12)
txt(box(s, 7.25, 4.95, 5.2, 1.5),
    "Honest: hotspots are highly persistent (naïve baseline already ~0.87 spatial). The model adds confidence "
    "bands + edge on change; the value is the operational system, not raw R².", 11.5, MUTE)
note(s, "If asked 'why an ensemble?' — HistGB + LightGBM decorrelate errors. Crucially, we report the TRUE "
        "future hold-out, not just CV, AND the persistence baseline. Owning that the forecast is partly "
        "persistence is what a rigorous team does — and the confidence bands are a real add.")

s = content("MODEL · OPTIMISATION", "Constrained patrol placement (Operations Research)")
bullets(s, 0.95, 1.85, 5.3, 4.5, [
    "Problem: place K patrols to cover the MOST congestion impact — not just rank by score.",
    "Method: MAX-COVERAGE via submodular greedy (≈(1−1/e) optimality guarantee).",
    "Each patrol covers its zone + zones within ≈1.2 km; impact counted once (no double-count).",
    "",
    "Covers materially MORE unique impact than naive top-N — same patrol budget — then sequenced into a "
    "road-following route via MapmyIndia.",
    "Live 'Deploy & Simulate' slider recomputes coverage, route and ROI in real time.",
], size=14, space=8)
ph(s, 6.5, 1.85, 5.9, 4.55, "Priorities & Deploy — optimised vs naive + route")
note(s, "This is the non-tautological intelligence: ranking by score stacks patrols on adjacent hotspots that "
        "overlap. Max-coverage spreads them to cover ~13 percentage points MORE unique impact with the same "
        "budget. That's a real OR contribution, not just analytics.")

s = content("ENFORCEMENT ANALYTICS", "Beyond ranking — the non-obvious intelligence")
bullets(s, 0.95, 1.85, 5.3, 4.6, [
    f"Coverage-gap: {cov.get('n_under_enforced','—')} severe hotspots current patrols UNDER-serve (high impact, low effort).",
    f"Repeat offenders: {o['vio_from_repeat_%']}% of violations from repeat vehicles (worst caught {o['max_by_one_vehicle']}×).",
    f"Emerging hotspots: {emg.get('n_emerging','—')} rising spots flagged for early action.",
    "Post-enforcement tracker: monthly improving vs worsening zones (the learning loop).",
    "Enforcement-bias correction: estimate true demand where patrols rarely go.",
    "Ward-level unit allocation + congestion cost (₹, illustrative range).",
], size=14, space=8)
ph(s, 6.5, 1.85, 5.9, 4.6, "Coverage-gap / Repeat Offenders / Trends")
note(s, "Lead with COVERAGE-GAP — it's the killer, non-obvious insight: 'here are severe chokepoints your "
        "current patrols are MISSING.' That's intelligence beyond 'patrol where violations already are'. "
        "Repeat-offender and emerging give additional levers.")

s = content("WHY TRUST IT", "Validated against an INDEPENDENT dataset")
card(s, 0.95, 1.85, 3.6, v["neighbourhood_pearson_res6"], "corr. with congestion density", GREEN, 1.35)
card(s, 4.75, 1.85, 3.6, f"{v['neighbourhood_events_top20pct_%']}%", "congestion in worst-20% areas", BLUE, 1.35)
card(s, 8.55, 1.85, 3.55, f"{v['neighbourhood_lift']}×", "more than random chance", RED, 1.35)
bullets(s, 0.95, 3.5, 5.3, 2.9, [
    "Cross-checked vs a separate congestion/accident event log.",
    "Controlled (partial-correlation) check: the link is driven by hotspot density — reported honestly.",
    "Quasi-precision: top-zone hit-rate vs independent events.",
    "Associational evidence, not causal proof.",
], size=13.5, space=8)
ph(s, 6.5, 3.5, 5.9, 2.9, "Validation tab")
note(s, "THE differentiator: we validate one dataset against a completely independent one. Worst-20% parking "
        "areas hold 63% of all independently-reported congestion — 3.15× random. Almost no other team will "
        "cross-validate datasets. Be explicit it's associational, not causal.")

# ════════════════════════════ 04
divider("04", "PRODUCT & IMPACT", "A live command center, deployable today")
note(prs.slides[-1], "Section 4: show the product, the workflow, the impact, and how it deploys.")

s = content("THE PRODUCT", "A live command center — 9 interactive views")
feat = [("Command Map", "Impact hexagons · 3D city · MapmyIndia"), ("Ask ParkSight", "Natural-language queries"),
        ("Live Ops", "Highest-risk zones for THIS hour"), ("Priorities & Deploy", "Optimise · route · ROI · export"),
        ("Forecast", "Risk surface + confidence bands"), ("Repeat Offenders", "Offender Pareto · deterrence"),
        ("Trends", "Improving/worsening · time-lapse"), ("Coverage & Context", "Under-enforced · bias · POI")]
for i, (t, b) in enumerate(feat):
    cx = 0.95 + (i % 4) * 3.0; cy = 1.9 + (i // 4) * 2.35
    rect(s, cx, cy, 2.85, 2.1, LIGHT, MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE, lw=1)
    rect(s, cx + 0.16, cy + 0.16, 0.42, 0.09, BLUE)
    tf = box(s, cx + 0.16, cy + 0.33, 2.55, 1.65)
    txt(tf, t, 13.5, INK, True, first=True); txt(tf, b, 11, MUTE, space=0)
txt(box(s, 0.95, 6.55, 11.7, 0.4), "Plus a one-click PDF Commander's Briefing and the independent Validation view.",
    12, MUTE)
note(s, "Don't read every card. Say: 'Nine views, one workflow — but three steal the show', then jump to the "
        "next slide / live demo.")

s = content("STANDOUT FEATURES", "What judges remember")
ph(s, 0.95, 1.85, 5.7, 2.2, "Ask ParkSight (natural-language)")
ph(s, 6.7, 1.85, 5.7, 2.2, "3D congestion city")
ph(s, 0.95, 4.2, 5.7, 2.2, "Live Ops — deploy this hour")
bullets(s, 6.7, 4.25, 5.7, 2.2, [
    "› Ask-in-English deployment queries (offline)",
    "› 3D extruded impact map (pydeck)",
    "› Live-Ops 'right now' scheduling",
    "› MapmyIndia / Streets / Satellite basemaps",
    "› One-click PDF Commander's Briefing",
], size=13, space=7)
note(s, "If doing a live demo, THIS is the moment: type a question into Ask ParkSight, flip the 3D city, drag "
        "the deploy slider. 60 seconds of interaction beats five slides.")

s = content("USE CASE", "From data to deployment, in one shift")
for i, (n, t, b) in enumerate([
        ("1", "Morning brief", "DCP opens the dashboard / PDF briefing: today's top zones + ward allocation."),
        ("2", "Deploy", "Sets patrol count → optimiser picks zones, MapmyIndia routes them."),
        ("3", "Act now", "Live-Ops shows the highest-risk zones for THIS hour; officers reposition."),
        ("4", "Learn", "Next month, the tracker shows which zones improved — close the loop.")]):
    cy = 1.95 + i * 1.18
    rect(s, 0.95, cy, 0.7, 0.92, BLUE if i % 2 == 0 else NAVY, MSO_SHAPE.OVAL)
    txt(box(s, 0.95, cy + 0.22, 0.7, 0.5), n, 20, WHITE, True, PP_ALIGN.CENTER, first=True)
    tf = box(s, 1.95, cy + 0.04, 10.4, 1.0)
    txt(tf, t, 15, INK, True, first=True); txt(tf, b, 12.5, MUTE, space=0)
note(s, "Tell it as a story of a DCP's shift — morning brief → deploy → act this hour → learn next month. "
        "Makes the abstract analytics concrete and operational.")

s = content("IMPACT & ROI", "Focus beats blanket patrolling")
card(s, 0.95, 1.9, 3.7, "~7% → 80%", "cells cover 80% of impact", GREEN)
card(s, 4.85, 1.9, 3.7, f"₹{cost['annual_cost_cr_low']}–{cost['annual_cost_cr_high']} cr", "congestion cost / yr (est.)", RED)
card(s, 8.75, 1.9, 3.6, "+~13 pp", "optimiser vs naive coverage", VIO)
bullets(s, 0.95, 3.8, 11.7, 2.6, [
    "Enforce ~7% of the city → address 80% of parking-induced congestion impact.",
    "Max-coverage optimisation covers more impact per patrol than naive ranking.",
    "A what-if ROI estimates violations & rupees averted (adjustable effectiveness slider; illustrative).",
    "Deployable today — on the police's own data and MapmyIndia's own maps.",
], size=15, space=11)
note(s, "The memorable line: 'Enforce 7% of the city, fix 80% of the problem.' Frame the ₹ figure as an "
        "illustrative range, not a precise claim — judges respect the honesty.")

s = content("WHY PARKSIGHT STANDS OUT", "Against a typical hackathon entry")
table(s, 0.95, 1.9, 11.45, [
    ["Dimension", "Typical entry", "ParkSight"],
    ["Output", "A dashboard / heatmap", "A deployable patrol PLAN (zones, route, units)"],
    ["Impact", "Counts violations", "Quantifies traffic impact (severity-weighted)"],
    ["Trust", "Self-reported", "Validated vs an INDEPENDENT congestion dataset"],
    ["Method", "One model", "Forecast + OR optimisation + uncertainty"],
    ["Partners", "Generic OSS maps", "MapmyIndia maps + routing, BTP data"],
    ["Rigour", "Best-case numbers", "Temporal hold-out + honest limitations"],
], col_w=[2.3, 4.4, 4.75], fs=11.5, row_h=0.5)
note(s, "Use this as the closing argument before logistics. Each row is a reason to rank us above a "
        "pretty-dashboard entry. The 'Trust' and 'Partners' rows are the strongest.")

s = content("DEPLOYMENT & SCALABILITY", "Ready to pilot, easy to scale")
bullets(s, 0.95, 1.9, 5.5, 4.5, [
    "Plugs into existing workflow:",
    "›  Nightly violation export → ParkSight refresh → dashboard + field plans.",
    "›  Officers get today's route on a phone; commanders get ward allocation + PDF brief.",
    "›  Live public demo on Streamlit Cloud; secrets-managed Mappls keys.",
], size=14, space=8)
bullets(s, 6.65, 1.9, 5.7, 4.5, [
    "Scales with one config block:",
    "›  City centre, bounding box, H3 resolution, severity weights are config-driven.",
    "›  Same pipeline runs on any city's violation feed.",
    "›  Reproducible build (~100 s) + unit tests + artifact caching.",
], size=14, space=8)
note(s, "Answers the 'can this actually be used / scaled?' question. No new hardware — it consumes the data the "
        "police already collect. Multi-city is a config change, not a rewrite.")

s = content("TECH STACK & PARTNERS", "Built on the provided real-world infrastructure")
rect(s, 6.55, 1.9, 0.012, 4.4, LINE)
bullets(s, 0.95, 1.9, 5.4, 4.5, [
    "Partners:",
    "›  MapmyIndia (Mappls) — map tiles + India-grade road routing (OAuth, cached)",
    "›  Bengaluru Traffic Police (ASTraM) — violation & congestion datasets",
    "",
    "Models & methods:",
    "›  HistGradientBoosting + LightGBM ensemble (forecast)",
    "›  Quantile GBM (uncertainty) · DBSCAN (clustering)",
    "›  Submodular max-coverage (optimisation) · NNLS (calibration)",
], size=13.5, space=7)
bullets(s, 6.85, 1.9, 5.5, 4.5, [
    "Engineering:",
    "›  Python · pandas · NumPy · scikit-learn · LightGBM",
    "›  Uber H3 · Plotly · pydeck · Streamlit",
    "›  OSRM (routing fallback) · OpenStreetMap",
    "",
    "Rigour:",
    "›  5-fold out-of-fold encoding · temporal hold-out",
    "›  unit tests (pytest) · config-driven · reproducible build",
], size=13.5, space=7)
note(s, "Highlight that we USED the partner infrastructure (MapmyIndia + BTP data) — a scoring signal — and "
        "that routing/maps gracefully fall back to OSS if keys are absent.")

s = content("LIMITATIONS & SCOPE", "What we're honest about")
bullets(s, 0.95, 1.9, 11.7, 4.4, [
    "›  We PROXY congestion (no live flow data provided); validated against an independent congestion log.",
    "›  Enforcement data = where patrols looked (selection bias) — surfaced and corrected.",
    "›  Temporal pattern = detection times (officer shifts) — framed as detection-risk, not raw demand.",
    "›  Validation is associational, not causal (controlled check shown).",
    "›  ₹ cost & enforcement effectiveness are illustrative ranges; forecast ≈ persistence + a small edge.",
    "›  Privacy: all IDs anonymised. One city, ~5 months; pipeline is config-driven to generalise.",
], size=14.5, space=11)
txt(box(s, 0.95, 6.45, 11.7, 0.45),
    "Owning these is the point: a validated, deployable decision-support tool — not over-claimed.", 13, BLUE, True)
note(s, "Do NOT skip this slide. In a government room, the team that states its own limitations earns more "
        "trust than the team that over-claims. It signals maturity and makes every other number believable.")

# Close
s = prs.slides.add_slide(BLANK); _bg(s, NAVY); rect(s, 0, 0, 0.22, 7.5, BLUE)
txt(box(s, 0.9, 2.3, 11.5, 1.1), "ParkSight turns parking data into traffic relief.", 30, WHITE, True)
txt(box(s, 0.9, 3.6, 11.7, 1.4),
    "Detect · quantify · forecast · optimise · validate — complete, validated, deployable.  "
    "Enforce 7% of the city, fix 80% of the problem.", 18, RGBColor(0xC7, 0xD4, 0xEA))
txt(box(s, 0.9, 6.4, 11.7, 0.4),
    "Live demo + repository in the submission  ·  Powered by MapmyIndia & Bengaluru Traffic Police data",
    12, RGBColor(0x8A, 0xA0, 0xC0))
note(s, "Close on the one-liner and invite the live demo. Thank the partners (MapmyIndia + BTP). "
        "Have the public Streamlit link ready to open.")

try:
    prs.save(str(ROOT / "ParkSight_Deck.pptx")); print("saved ParkSight_Deck.pptx with", len(prs.slides._sldIdLst), "slides")
except PermissionError:
    prs.save(str(ROOT / "ParkSight_Deck_v2.pptx")); print("locked -> saved ParkSight_Deck_v2.pptx")
